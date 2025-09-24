import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

# 로컬 모듈 임포트
import models, schemas
from database import engine, get_db
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

# --- 로깅, FastAPI 앱 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = FastAPI(
    title="Jumokase API",
    description="벡터 검색 및 RAG 기반 전통주 추천 시스템",
    version="2.0.0",
)

# --- LangChain 및 임베딩 모델 설정 ---
llm = ChatOpenAI(model="gpt-4o", temperature=0.5)
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

reasoning_prompt = PromptTemplate.from_template(
    """
    사용자가 아래와 같은 질문을 했습니다.
    사용자 질문: "{user_query}"

    이 질문에 대해 당신은 아래 정보를 가진 전통주를 추천하려고 합니다.
    전통주 정보:
    {liquor_info}

    사용자의 질문과 전통주의 상세 정보를 모두 고려하여, 추천하는 이유를 1~2문장의 간결하고 매력적인 문장으로 작성해주세요.
    """
)
reasoning_chain = reasoning_prompt | llm | StrOutputParser()

pairing_parser = JsonOutputParser(pydantic_object=schemas.FoodPairingResponse)
pairing_prompt = PromptTemplate(
    template="""
    당신은 음식 페어링 전문가입니다. 아래 전통주의 상세 정보를 보고, 이 술과 가장 잘 어울리는 구체적인 음식 '하나'만 추천해주세요.
    오직 음식 이름만 답변해야 합니다. 다른 설명은 절대 추가하지 마세요. {format_instructions}

    전통주 상세 정보:
    {liquor_info}
    """,
    input_variables=["liquor_info"],
    partial_variables={"format_instructions": pairing_parser.get_format_instructions()},
)
pairing_chain = pairing_prompt | llm | pairing_parser

# --- 애플리케이션 시작 이벤트 ---
@app.on_event("startup")
async def startup_event():
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()
    
    models.Base.metadata.create_all(bind=engine)
    logging.info("데이터베이스 테이블 및 pgvector 확장 기능이 준비되었습니다.")

# --- API 엔드포인트 구현 ---
@app.post("/liquors/recommendations", response_model=List[schemas.RecommendationResponseItem])
async def get_recommendations(request: schemas.RecommendationRequest, db: Session = Depends(get_db)):
    logging.info(f"추천 요청 수신: {request.userQuery}")
    try:
        query_embedding = await embedding_model.aembed_query(request.userQuery)

        similar_liquors = db.query(models.Liquor).order_by(
            models.Liquor.feature_embedding.cosine_distance(query_embedding)
        ).limit(3).all()

        if not similar_liquors:
            logging.info("유사한 주류를 찾지 못했습니다.")
            return []

        tasks = []
        for liquor in similar_liquors:
            rich_context = (
                f"술 이름: {liquor.name}\n"
                f"설명: {liquor.description}\n"
                f"주요 특징: {liquor.features}\n"
                f"주요 성분: {liquor.ingredients}\n"
                f"알콜 도수: {liquor.alcohol_content}도\n"
                f"수상 경력: {liquor.awards}"
            )
            task = reasoning_chain.ainvoke({
                "user_query": request.userQuery,
                "liquor_info": rich_context
            })
            tasks.append(task)
        
        reasons = await asyncio.gather(*tasks)

        response_data = [
            {"id": similar_liquors[i].id, "liquorName": similar_liquors[i].name, "reason": reasons[i]}
            for i in range(len(similar_liquors))
        ]
        
        logging.info(f"추천 응답 전송: {response_data}")
        return response_data
    except Exception as e:
        logging.error(f"추천 생성 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="추천 생성 중 오류가 발생했습니다.")

@app.post("/liquors/{liquor_id}/pairings", response_model=schemas.FoodPairingResponse)
async def get_food_pairing(liquor_id: int, db: Session = Depends(get_db)):
    logging.info(f"페어링 요청 수신: liquor_id={liquor_id}")
    
    selected_liquor = db.query(models.Liquor).filter(models.Liquor.id == liquor_id).first()
    
    if not selected_liquor:
        logging.warning(f"ID {liquor_id}에 해당하는 주류를 찾을 수 없습니다.")
        raise HTTPException(status_code=404, detail="해당 ID의 주류를 찾을 수 없습니다.")
    
    try:
        rich_context = (
            f"술 이름: {selected_liquor.name}\n"
            f"설명: {selected_liquor.description}\n"
            f"주요 특징: {selected_liquor.features}\n"
            f"알콜 도수: {selected_liquor.alcohol_content}도"
        )
        pairing_result = await pairing_chain.ainvoke({"liquor_info": rich_context})
        
        logging.info(f"페어링 응답 전송: {pairing_result}")
        return pairing_result
    except Exception as e:
        logging.error(f"페어링 생성 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="페어링 추천 생성 중 오류가 발생했습니다.")

@app.get("/recommendations", response_model=List[schemas.Recommendation])
async def get_all_recommendations(db: Session = Depends(get_db)):
    logging.info("모든 추천 기록 조회 요청 수신")
    try:
        recommendations = db.query(models.Recommendation).all()
        logging.info(f"총 {len(recommendations)}개의 추천 기록을 반환합니다.")
        return recommendations
    except Exception as e:
        logging.error(f"추천 기록 조회 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="추천 기록 조회 중 오류가 발생했습니다.")