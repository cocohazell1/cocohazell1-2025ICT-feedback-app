import streamlit as st
import os
from openai import OpenAI
# from dotenv import load_dotenv # 이 줄은 주석 처리하거나 삭제해도 됩니다.
import fitz
import io
import time
import pandas as pd
import re

# --- API 키 로딩 수정 ---
# Streamlit Cloud의 Secrets 또는 로컬 환경 변수에서 API 키 로드 시도
# 1순위: Streamlit Cloud Secrets
api_key = st.secrets.get("OPENAI_API_KEY")

# 2순위: 로컬 환경 변수 (선택 사항 - 로컬 테스트용)
# if api_key is None:
#     api_key = os.getenv("OPENAI_API_KEY")

# 3순위: 로컬 .env 파일 (선택 사항 - 로컬 테스트용)
# if api_key is None:
#     from dotenv import load_dotenv
#     load_dotenv()
#     api_key = os.getenv("OPENAI_API_KEY")

# 최종 API 키 확인
if api_key is None:
    st.error("OpenAI API 키를 찾을 수 없습니다. Streamlit Cloud Secrets 설정을 확인하세요.")
    st.stop() # 키 없으면 앱 중지

# OpenAI 클라이언트 초기화 (이후 코드는 동일)
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"OpenAI 클라이언트 초기화 오류: {e}")
    st.stop()

# ... (파일의 나머지 코드는 그대로 둡니다) ...

# --- 함수: PDF에서 텍스트 추출 ---
def extract_text_from_pdf(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            full_text = "".join(page.get_text() for page in doc) # 리스트 컴프리헨션으로 간결화
        return full_text
    except Exception as e:
        st.error(f"PDF 처리 오류: {e}")
        st.warning("텍스트 기반 PDF인지, 파일 손상 여부 확인.")
        return None

# --- 함수: 피드백 텍스트에서 점수 추출 ---
def parse_scores_from_feedback(feedback_text):
    """GPT 피드백 텍스트에서 점수를 파싱하는 함수"""
    scores = {}
    # 점수 형식을 찾기 위한 정규 표현식 패턴 (예: "항목명: 8/10")
    # 콜론(:), 공백, 숫자, 슬래시(/), 숫자, /10 형식을 찾음
    pattern = re.compile(r"([\w\s/]+?):\s*(\d{1,2})\s*/\s*10")

    # 피드백 텍스트를 줄 단위로 검사
    for line in feedback_text.splitlines():
        match = pattern.search(line)
        if match:
            category = match.group(1).strip() # 항목명 추출 및 공백 제거
            score = int(match.group(2))       # 점수 추출 및 정수 변환
            # 미리 정의된 카테고리 이름과 유사하게 매칭 (선택 사항, 정확도 향상 목적)
            # 예: '명확성 및 논리성'이 포함된 라인이면 category를 '명확성 및 논리성'으로 통일
            if "명확성" in category or "논리성" in category:
                scores['명확성 및 논리성'] = score
            elif "시장 분석" in category:
                scores['시장 분석'] = score
            elif "사업 모델" in category:
                scores['사업 모델'] = score
            elif "실행 계획" in category:
                scores['실행 계획'] = score
            elif "재무 계획" in category:
                scores['재무 계획'] = score
            elif "차별점" in category or "강점" in category:
                scores['차별점 및 강점'] = score
            elif "위험" in category or "약점" in category:
                scores['위험 요인 관리'] = score
            else: # 정의되지 않은 항목도 일단 추가 (필요시 조정)
                scores[category] = score

    # 기본 카테고리 추가 (만약 파싱되지 않았다면 0점으로) - 선택 사항
    default_categories = ['명확성 및 논리성', '시장 분석', '사업 모델', '실행 계획', '재무 계획', '차별점 및 강점', '위험 요인 관리']
    for cat in default_categories:
        if cat not in scores:
            scores[cat] = 0 # 점수가 없으면 0점으로 표시

    return scores


# --- Streamlit 앱 인터페이스 ---
st.set_page_config(page_title="사업계획서 AI 피드백", layout="wide") # 페이지 넓게 사용
st.title("🚀 사업계획서 자동 피드백 및 점수 시각화")
st.markdown("---")

# 파일 업로드 섹션
st.header("📄 사업계획서 PDF 업로드")
uploaded_file = st.file_uploader("텍스트 기반 PDF 파일을 업로드하세요.", type="pdf")
st.caption("💡 Tip: 스캔된 이미지 PDF는 텍스트 인식이 어려울 수 있습니다.")

# 피드백 요청 버튼
submit_button = st.button("🤖 AI 피드백 및 점수 요청하기")

st.markdown("---")

# --- 피드백/점수 생성 및 표시 로직 ---
feedback = None # <--- 이 줄을 추가하세요
if submit_button and uploaded_file is not None:
    # 세션 상태를 사용하여 결과를 저장하고 재실행 시 유지 (선택 사항)
    # if 'feedback' not in st.session_state or st.session_state.uploaded_file_name != uploaded_file.name:

    try:
        with st.spinner('🔄 PDF 읽고 AI 분석 중... (점수 포함)'):
            # 1. PDF 텍스트 추출
            business_plan_text = extract_text_from_pdf(uploaded_file)

            # 2. 텍스트 추출 성공 시 AI 호출
            if business_plan_text:
                # --- GPT 프롬프트 수정: 점수 부여 요청 추가 ---
                prompt = f"""
                당신은 매우 경험 많은 사업 컨설턴트이자 투자 심사역입니다.
                다음 사업계획서 내용을 검토하고, 구체적이고 실행 가능한 피드백과 함께 **각 항목별로 1점에서 10점 사이의 점수를 부여해주세요.** (1점: 매우 부족, 10점: 매우 우수)

                [피드백 항목 및 점수 평가 기준]
                1.  **명확성 및 논리성:** 내용이 이해하기 쉽고 논리적으로 잘 연결되는가? (핵심 메시지 전달력)
                2.  **시장 분석:** 타겟 시장 정의, 시장 크기, 경쟁 환경 분석이 구체적이고 현실적인가?
                3.  **사업 모델:** 수익 창출 방식(BM)이 명확하고 설득력 있으며, 지속 가능한가?
                4.  **실행 계획:** 목표 달성을 위한 구체적인 액션 플랜, 일정, 자원 계획이 제시되었는가?
                5.  **재무 계획:** 매출 추정, 비용 구조, 손익분기점, 자금 조달 계획 등이 합리적이고 구체적인가? (언급되지 않았거나 부족하면 낮은 점수)
                6.  **차별점 및 강점:** 경쟁 우위 요소(기술, 팀, 특허 등)가 명확하고 강력하게 드러나는가?
                7.  **위험 요인 관리:** 예상되는 사업적 위험(시장, 기술, 재무 등)을 인지하고 있으며, 이에 대한 대응 방안이 고려되었는가?

                [출력 형식]
                - 먼저 각 항목에 대한 상세한 텍스트 피드백 (강점, 약점, 개선 제안)을 작성해주세요.
                - **피드백 마지막 부분에 아래와 같은 형식으로 각 항목별 점수를 명확하게 요약해주세요.**

                [점수 요약]
                명확성 및 논리성: 점수/10
                시장 분석: 점수/10
                사업 모델: 점수/10
                실행 계획: 점수/10
                재무 계획: 점수/10 (내용 부족 시 1~3점 부여 가능)
                차별점 및 강점: 점수/10
                위험 요인 관리: 점수/10

                [사업계획서 내용]
                {business_plan_text}
                """

                # OpenAI API 호출
                response = client.chat.completions.create(
                    model="gpt-4o", # 점수 부여 등 복잡한 작업에는 GPT-4 이상 모델 권장 (없으면 gpt-3.5-turbo)
                    messages=[
                        {"role": "system", "content": "당신은 사업 계획 분석 및 평가 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000, # 점수 및 상세 피드백 위해 토큰 수 늘림 (비용 주의)
                    temperature=0.5, # 점수 부여의 일관성을 위해 약간 낮춤
                )

                # 결과 저장 (세션 상태 사용 시)
                # st.session_state.feedback = response.choices[0].message.content
                # st.session_state.uploaded_file_name = uploaded_file.name
                feedback = response.choices[0].message.content

            else:
                st.warning("PDF에서 텍스트를 추출하지 못했습니다.")
                # st.session_state.feedback = None # 세션 상태 사용 시 초기화
                feedback = None

    except Exception as e:
        st.error(f"⚠️ AI 피드백/점수 생성 중 오류: {e}")
        # st.session_state.feedback = None # 세션 상태 사용 시 초기화
        feedback = None

# --- 결과 표시 ---
# if 'feedback' in st.session_state and st.session_state.feedback: # 세션 상태 사용 시
if feedback: # feedback 변수가 존재하고 내용이 있을 때
    # feedback = st.session_state.feedback # 세션 상태 사용 시

    # 1. 전체 피드백 텍스트 표시
    st.header("💡 AI 피드백 결과")
    st.markdown(feedback) # 마크다운으로 보기 좋게 표시

    st.markdown("---") # 구분선

    # 2. 점수 추출 및 시각화
    st.header("📊 피드백 점수 시각화")
    scores = parse_scores_from_feedback(feedback) # 점수 파싱 함수 호출

    if scores: # 점수가 성공적으로 파싱되었으면
        try:
            # 점수 데이터를 Pandas DataFrame으로 변환 (차트 입력용)
            # 카테고리 순서 고정 (선택 사항)
            ordered_categories = ['명확성 및 논리성', '시장 분석', '사업 모델', '실행 계획', '재무 계획', '차별점 및 강점', '위험 요인 관리']
            ordered_scores = {cat: scores.get(cat, 0) for cat in ordered_categories} # 순서대로 점수 가져오기 (없으면 0)

            scores_df = pd.DataFrame.from_dict(ordered_scores, orient='index', columns=['점수'])

            # 막대 그래프 표시
            st.bar_chart(scores_df, height=400) # 높이 조절 가능

            # 점수 테이블도 함께 표시 (선택 사항)
            st.subheader("세부 점수표")
            st.table(scores_df)

        except Exception as e:
            st.error(f"점수 시각화 중 오류 발생: {e}")
            st.warning("피드백 텍스트에서 점수 형식을 제대로 인식하지 못했을 수 있습니다. GPT 출력을 확인하거나 파싱 로직 수정이 필요할 수 있습니다.")

    else:
        st.warning("피드백 텍스트에서 점수를 추출하지 못했습니다. GPT가 요청된 형식으로 점수를 반환했는지 확인해주세요.")

elif submit_button and uploaded_file is None:
    st.warning("⚠️ 먼저 PDF 파일을 업로드해주세요.")

# --- 앱 하단 정보 ---
st.markdown("---")
st.caption("Powered by Streamlit, OpenAI GPT, PyMuPDF & Pandas")