import os
import pandas as pd
import json
import logging
import re
import asyncio # (추가) 비동기 처리를 위해
from sqlalchemy.orm import Session
from sqlalchemy import text

# 우리 프로젝트의 SQLAlchemy 설정과 모델을 그대로 가져와 사용합니다.
from database import engine, SessionLocal
from models import Base, Liquor, Recommendation
from langchain_openai import OpenAIEmbeddings # (추가) 임베딩 모델 직접 사용

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CSV_FILE = "liquor_with_embedding_v2.csv"
# (추가) LangChain 임베딩 모델 초기화
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

def setup_database(db: Session):
    logging.info("pgvector 확장 기능 활성화를 시도합니다...")
    db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    db.commit()
    logging.info("pgvector 확장 기능이 준비되었습니다.")

    logging.info("기존 테이블을 삭제하고 새로 생성합니다...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logging.info("테이블 생성이 완료되었습니다.")

async def insert_liquor_data(db: Session):
    """
    CSV 파일에서 주류 데이터를 읽고, OpenAI API로 임베딩을 생성한 뒤 DB에 삽입합니다.
    """
    if not os.path.exists(CSV_FILE):
        logging.warning(f"'{CSV_FILE}' 파일을 찾을 수 없습니다. 데이터 삽입을 건너뜁니다.")
        return

    logging.info(f"'{CSV_FILE}' 파일에서 데이터를 읽어옵니다...")
    df = pd.read_csv(CSV_FILE)
    
    original_rows = len(df)
    df.drop_duplicates(subset=['제품명'], keep='first', inplace=True)
    if original_rows > len(df):
        logging.info(f"{original_rows - len(df)}개의 중복된 주류 데이터를 제거했습니다.")
    
    # --- (핵심 수정) ---
    # 중복 제거 후 인덱스를 0부터 순서대로 다시 정렬합니다.
    df.reset_index(drop=True, inplace=True)
    # --------------------
    
    df = df.where(pd.notnull(df), None)

    logging.info("주류 특징에 대한 임베딩을 생성합니다... (데이터 양에 따라 시간이 걸릴 수 있습니다)")
    texts_to_embed = df.apply(
        lambda row: f"특징: {row.get('특징', '')}. 소개: {row.get('제품소개', '')}",
        axis=1
    ).tolist()
    
    embeddings = await embedding_model.aembed_documents(texts_to_embed)
    logging.info("임베딩 생성이 완료되었습니다.")

    logging.info(f"총 {len(df)}개의 주류 데이터를 DB에 삽입합니다...")
    
    for index, row in df.iterrows():
        # 데이터 전처리 및 타입 변환 ...
        # (이하 로직은 이전과 동일하며, 이제 index가 순차적이라 오류가 발생하지 않습니다)
        processed_volume = None
        if row["용량"]:
            try:
                numeric_part = re.search(r'\d+', str(row["용량"]))
                if numeric_part:
                    processed_volume = int(numeric_part.group(0))
            except (ValueError, TypeError):
                logging.warning(f"'{row['제품명']}'의 용량('{row['용량']}')을 숫자로 변환할 수 없습니다.")
        
        processed_alcohol = None
        if row["알콜도수"]:
            try:
                numeric_part = re.search(r'[\d\.]+', str(row["알콜도수"]))
                if numeric_part:
                    processed_alcohol = float(numeric_part.group(0))
            except (ValueError, TypeError):
                logging.warning(f"'{row['제품명']}'의 알콜도수('{row['알콜도수']}')를 숫자로 변환할 수 없습니다.")

        liquor_obj = Liquor(
            name=row["제품명"],
            description=row["제품소개"],
            alcohol_content=processed_alcohol,
            volume=processed_volume,
            ingredients=row["성분"],
            notes=row["특이사항"],
            features=row["특징"],
            is_for_sale=True if row["판매여부"] == 'Y' else False,
            brewery_name=row["양조장"],
            brewery_address=row["양조장주소"],
            homepage_url=row["홈페이지주소"],
            awards=row["수상경력"],
            feature_embedding=embeddings[index]
        )
        db.add(liquor_obj)

    db.commit()
    logging.info("주류 데이터 삽입이 완료되었습니다.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        setup_database(db)
        # (수정) async 함수를 실행하기 위해 asyncio.run() 사용
        asyncio.run(insert_liquor_data(db))
        
        logging.info("모든 작업이 성공적으로 완료되었습니다!")
    except Exception as e:
        logging.error(f"작업 중 오류가 발생했습니다: {e}")
        db.rollback()
    finally:
        db.close()