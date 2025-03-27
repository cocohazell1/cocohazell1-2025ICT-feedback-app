import streamlit as st
import os
from openai import OpenAI
import fitz
import io
import time
import pandas as pd
import re
import plotly.graph_objs as plt
from typing import Dict, Any

class BusinessPlanAnalyzer:
    def __init__(self):
        # API 키 설정 및 클라이언트 초기화
        self.api_key = self._load_api_key()
        self.client = self._initialize_openai_client()

    def _load_api_key(self) -> str:
        """API 키를 안전하게 로드하는 메서드"""
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OpenAI API 키를 찾을 수 없습니다. Streamlit Cloud Secrets 설정을 확인하세요.")
            st.stop()
        return api_key

    def _initialize_openai_client(self) -> OpenAI:
        """OpenAI 클라이언트를 초기화하는 메서드"""
        try:
            return OpenAI(api_key=self.api_key)
        except Exception as e:
            st.error(f"OpenAI 클라이언트 초기화 오류: {e}")
            st.stop()

    def extract_text_from_pdf(self, uploaded_file) -> str:
        """PDF에서 텍스트를 추출하는 메서드"""
        try:
            file_bytes = uploaded_file.getvalue()
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                full_text = "".join(page.get_text() for page in doc)
            return full_text
        except Exception as e:
            st.error(f"PDF 처리 오류: {e}")
            st.warning("텍스트 기반 PDF인지, 파일 손상 여부를 확인해주세요.")
            return None

    def generate_ai_feedback(self, business_plan_text: str) -> str:
        """AI를 통해 사업계획서 피드백을 생성하는 메서드"""
        prompt = f"""
        [전문 투자 심사역 관점 사업계획서 종합 평가]

        당신은 10년 경력의 벤처캐피털 심사역입니다. 다음 사업계획서를 극도로 세밀하고 전문적인 관점에서 분석해주세요.

        평가 프레임워크:
        1. 명확성 및 논리성 (배점 15점)
        - 사업 아이디어의 명확성
        - 논리적 일관성
        - 스토리텔링 능력

        2. 시장 분석 (배점 20점)
        - 시장 규모 및 성장성
        - 시장 세분화 전략
        - 경쟁사 분석의 깊이
        - TAM, SAM, SOM 분석 여부

        3. 사업 모델 (배점 20점)
        - 수익 모델의 혁신성
        - 확장성
        - 수익 streams 다양성
        - 고객 획득 전략

        4. 실행 계획 (배점 15점)
        - 구체적인 마일스톤
        - 자원 배분 계획
        - 타임라인의 현실성
        - 리스크 대응 방안

        5. 재무 계획 (배점 15점)
        - 수익 추정의 근거
        - 비용 구조 분석
        - 손익분기점 계산
        - 투자 대비 ROI 전망

6. 기술/제품 차별성 (배점 10점)
        - 기술적 혁신성
        - 특허/지적재산권
        - 경쟁사 대비 기술적 우위성

        7. 팀의 역량 (배점 5점)
        - 창업팀의 전문성
        - 관련 산업 경험
        - 성공 가능성을 보여주는 배경

        [요구사항]
        - 각 항목별로 상세하고 구체적인 피드백 제공
        - 각 평가 영역의 점수를 100점 만점으로 환산
        - 전체 점수와 함께 상세 개선 방안 제시
        - 투자 결정에 도움되는 핵심 인사이트 강조

        [사업계획서 내용]
        {business_plan_text}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 10년 경력의 전문 투자 심사역입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.6
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"AI 피드백 생성 중 오류: {e}")
            return None

    def parse_detailed_scores(self, feedback_text: str) -> Dict[str, float]:
        """피드백 텍스트에서 점수를 추출하는 고급 메서드"""
        scores = {}
        categories = [
            '명확성 및 논리성', '시장 분석', '사업 모델',
            '실행 계획', '재무 계획', '기술/제품 차별성', '팀의 역량'
        ]

        for category in categories:
            pattern = re.compile(rf"{category}.*?(\d+(?:\.\d+)?)/100", re.DOTALL)
            match = pattern.search(feedback_text)
            if match:
                scores[category] = float(match.group(1))
            else:
                scores[category] = 0.0

        return scores

    def visualize_scores(self, scores: Dict[str, float]):
        """Plotly를 사용한 세련된 점수 시각화"""
        categories = list(scores.keys())
        values = list(scores.values())

        fig = plt.Figure(data=[
            plt.Bar(
                x=categories,
                y=values,
                marker_color='rgba(58, 71, 80, 0.6)',
                marker_line_color='rgba(58, 71, 80, 1.0)',
                marker_line_width=1.5,
            )
        ])

        fig.update_layout(
            title='사업계획서 종합 평가 점수',
            xaxis_title='평가 영역',
            yaxis_title='점수 (100점 만점)',
            yaxis_range=[0, 100],
            template='plotly_white',
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

def main():
    st.set_page_config(
        page_title="AI 사업계획서 심층 분석",
        page_icon="🚀",
        layout="wide"
    )

    st.title("🚀 사업계획서 AI 심층 분석 플랫폼")
    st.markdown("---")

    # 파일 업로드 섹션
    st.header("📄 사업계획서 PDF 업로드")
    uploaded_file = st.file_uploader(
        "텍스트 기반 PDF 파일을 업로드하세요.",
        type="pdf",
        help="스캔된 이미지 PDF는 텍스트 인식에 어려움이 있을 수 있습니다."
    )

    analyzer = BusinessPlanAnalyzer()

    if st.button("🤖 AI 심층 분석 시작", type="primary"):
        if uploaded_file is not None:
            with st.spinner('🔄 AI가 사업계획서를 분석 중입니다...'):
                # PDF 텍스트 추출
                business_plan_text = analyzer.extract_text_from_pdf(uploaded_file)

                if business_plan_text:
                    # AI 피드백 생성
                    feedback = analyzer.generate_ai_feedback(business_plan_text)

                    if feedback:
                        # 피드백 표시
                        st.header("💡 AI 심층 분석 결과")
                        st.markdown(feedback)

                        st.markdown("---")

                        # 점수 추출 및 시각화
                        st.header("📊 세부 평가 점수")
                        scores = analyzer.parse_detailed_scores(feedback)

                        if scores:
                            analyzer.visualize_scores(scores)

                            # 점수 테이블
                            st.subheader("평가 영역별 점수")
                            score_df = pd.DataFrame.from_dict(
                                scores,
                                orient='index',
                                columns=['점수']
                            )
                            st.table(score_df)
                        else:
                            st.warning("점수 추출에 실패했습니다.")
                    else:
                        st.error("AI 분석 중 오류가 발생했습니다.")
                else:
                    st.warning("PDF에서 텍스트를 추출하지 못했습니다.")
        else:
            st.warning("📋 먼저 PDF 파일을 업로드해주세요.")

    # 앱 하단 정보
    st.markdown("---")
    st.caption("Powered by Streamlit, OpenAI GPT-4, PyMuPDF, Plotly")

if __name__ == "__main__":
    main()