import os
import pandas as pd
import logging
from sqlalchemy.orm import Session

# 프로젝트의 SQLAlchemy 설정과 모델을 그대로 가져와 사용합니다.
from database import SessionLocal
from models import Recommendation

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CSV_FILE = "traditional_liquor_dummy.csv"

def insert_recommendation_data(db: Session):
    """
    CSV 파일에서 추천 기록 데이터를 읽어와 DB의 recommendations 테이블에 삽입합니다.
    """
    if not os.path.exists(CSV_FILE):
        logging.error(f"'{CSV_FILE}' 파일을 찾을 수 없습니다. 스크립트를 종료합니다.")
        return

    try:
        logging.info(f"기존 recommendations 테이블의 모든 데이터를 삭제합니다...")
        db.query(Recommendation).delete()
        db.commit()

        logging.info(f"'{CSV_FILE}' 파일에서 추천 기록 데이터를 읽어옵니다...")
        df = pd.read_csv(CSV_FILE)
        df = df.where(pd.notnull(df), None)

        logging.info(f"총 {len(df)}개의 추천 기록을 DB에 삽입합니다...")

        for _, row in df.iterrows():
            recommendation_obj = Recommendation(
                age=row["age"],
                sex=row["sex"],
                drinkCount=row["drinkCount"],
                liquorName=row["liquorName"],
                reason=row["reason"],
                userQuery=row["userQuery"]
                # userQuery는 현재 Recommendation 모델에 없으므로 추가가 필요합니다.
                # 우선은 있는 필드만으로 진행합니다.
            )
            db.add(recommendation_obj)
        
        db.commit()
        logging.info("추천 기록 데이터 삽입이 완료되었습니다.")

    except Exception as e:
        logging.error(f"데이터 삽입 중 오류 발생: {e}")
        db.rollback()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        insert_recommendation_data(db)
        logging.info("모든 작업이 성공적으로 완료되었습니다!")
    finally:
        db.close()