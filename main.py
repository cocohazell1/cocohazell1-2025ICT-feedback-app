import streamlit as st
import os
from openai import OpenAI
import fitz
import io
import time
import pandas as pd
import re
import plotly.graph_objs as go
from typing import Dict, Any, List

class VeteranVCAnalyzer:
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
        """AI를 통해 사업계획서 심층 피드백을 생성하는 메서드"""
        prompt = f"""
        [극단적 정밀성의 벤처캐피털 심사 프레임워크]

        평가 배경: 2025년 현재, 글로벌 벤처투자 시장은 전례 없는 엄격성과 선별성을 요구하고 있습니다. 
        단 0.1%만이 투자 유치에 성공하는 극도로 경쟁적인 생태계입니다.

        [차별화된 평가 프레임워크: 다차원적 심층 분석]

        1. 명확성 및 논리성 (20점, 최고 엄격)
        - 사업 아이디어의 논리적 완결성
        - 인과관계의 명확성
        - 가설 검증 방법론
        - 잠재적 반론에 대한 선제적 대응

        2. 시장 분석 (25점, 데이터 기반 심층 분석)
        - 거시/미시 시장 세분화 수준
        - 글로벌 벤치마킹 데이터
        - 시장 진입 장벽 분석
        - ICP(Ideal Customer Profile) 정밀도
        - 글로벌 확장 가능성
        - 장기/단기 시장 트렌드 예측

        3. 사업 모델 (20점, 혁신성 평가)
        - 수익 모델의 지속가능성
        - 차별화된 가치제안
        - 고객 획득 비용(CAC) 최적화
        - 스케일업 메커니즘
        - 수익 다각화 전략
        - 기술적/운영적 모오트(Moat) 구축

        4. 실행 계획 (15점, 실현 가능성)
        - 마일스톤의 구체성
        - 리스크 시나리오별 대응 전략
        - 자원 배분의 효율성
        - 민첩성과 적응력
        - 실행 팀의 실행력 평가

        5. 재무 계획 (15점, 투자 관점)
        - 재무 모델링의 보수성
        - 투자 대비 ROI 전망
        - 자금 소진율(Burn Rate) 분석
        - 손익분기점의 현실성
        - 추가 투자 유치 가능성

        6. 기술/제품 차별성 (10점, 기술 혁신성)
        - 기술의 파괴력
        - 특허/지적재산권 포트폴리오
        - 기술적 장벽
        - 경쟁사 대비 절대적 우위성

        7. 팀의 역량 (5점, 핵심 차별점)
        - 개인/팀 레벨의 실행 이력
        - 산업 내 네트워크
        - 과거 성과의 지속성
        - 학습 및 적응 능력

        [평가 원칙]
        - 모든 평가는 객관적 근거에 기반
        - 가능성보다는 검증된 실행력 중심
        - 잠재적 투자 리스크의 극소화

        [분석 요구사항]
        - 각 영역별 정확한 점수 산정
        - 구체적인 개선 방안 제시
        - 투자 결정에 직접적인 인사이트 제공
        - 글로벌 스탠다드 관점에서의 평가

        [사업계획서 내용]
        {business_plan_text}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 25년 경력의 글로벌 벤처캐피털 파트너입니다. 극도로 정밀하고 엄격한 투자 심사 접근법을 사용합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"AI 피드백 생성 중 오류: {e}")
            return None

    def parse_detailed_scores(self, feedback_text: str) -> Dict[str, Dict[str, Any]]:
        """피드백 텍스트에서 점수와 세부 평가 내용을 추출하는 고급 메서드"""
        scores = {}
        categories = [
            '명확성 및 논리성', '시장 분석', '사업 모델',
            '실행 계획', '재무 계획', '기술/제품 차별성', '팀의 역량'
        ]

        for category in categories:
            # 점수 추출
            score_pattern = re.compile(rf"{category}.*?(\d+(?:\.\d+)?)/(\d+)", re.DOTALL)
            score_match = score_pattern.search(feedback_text)

            # 세부 평가 내용 추출
            detail_pattern = re.compile(rf"{category}.*?(\d+(?:\.\d+)?)/\d+\s*(.+?)(?=\n\n|\n\d|\Z)", re.DOTALL | re.MULTILINE)
            detail_match = detail_pattern.search(feedback_text)

            if score_match and detail_match:
                score = float(score_match.group(1))
                max_score = int(score_match.group(2))
                detail = detail_match.group(2).strip()

                scores[category] = {
                    'score': score,
                    'max_score': max_score,
                    'details': detail
                }
            else:
                scores[category] = {
                    'score': 0.0,
                    'max_score': 20,
                    'details': '평가 정보 없음'
                }

        return scores

    def visualize_scores(self, scores: Dict[str, Dict[str, Any]]):
        """인터랙티브하고 풍부한 Plotly 시각화"""
        categories = list(scores.keys())
        values = [score_data['score'] for score_data in scores.values()]
        max_scores = [score_data['max_score'] for score_data in scores.values()]

        # 레이더 차트
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            line_color='rgba(0, 128, 255, 0.7)',
            fillcolor='rgba(0, 128, 255, 0.3)'
        ))

        fig_radar.update_layout(
            title='사업계획서 다차원 평가 분석',
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(max_scores)]
                )
            ),
            height=600
        )

        # 막대 그래프
        fig_bar = go.Figure(data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color='rgba(58, 71, 80, 0.6)',
                text=[f'{v:.1f}/{max_scores[i]}' for i, v in enumerate(values)],
                textposition='auto',
            )
        ])

        fig_bar.update_layout(
            title='평가 영역별 점수 상세 분석',
            xaxis_title='평가 영역',
            yaxis_title='점수',
            yaxis_range=[0, max(max_scores)],
            height=500
        )

        # Streamlit에 차트 표시
        st.plotly_chart(fig_radar, use_container_width=True)
        st.plotly_chart(fig_bar, use_container_width=True)

        # 세부 점수 및 평가 내용 테이블
        st.subheader("📊 평가 영역별 상세 점수 및 평가")
        score_details = []
        for category, data in scores.items():
            score_details.append({
                '평가 영역': category,
                '획득 점수': f"{data['score']:.1f}/{data['max_score']}",
                '평가 세부 내용': data['details']
            })

        score_df = pd.DataFrame(score_details)
        st.table(score_df)

def main():
    st.set_page_config(
        page_title="베테랑 VC의 사업계획서 심층 분석",
        page_icon="🔍",
        layout="wide"
    )

    st.title("🔍 글로벌 벤처캐피털 심층 분석 플랫폼")
    st.markdown("---")

    st.header("📄 사업계획서 PDF 업로드")
    uploaded_file = st.file_uploader(
        "텍스트 기반 PDF 파일을 업로드하세요.",
        type="pdf",
        help="정확한 분석을 위해 명확한 텍스트 기반 PDF를 권장합니다."
    )

    analyzer = VeteranVCAnalyzer()

    if st.button("🚀 심층 투자 분석 시작", type="primary"):
        if uploaded_file is not None:
            with st.spinner('🔬 베테랑 VC가 사업계획서를 정밀 분석 중...'):
                # PDF 텍스트 추출
                business_plan_text = analyzer.extract_text_from_pdf(uploaded_file)

                if business_plan_text:
                    # AI 피드백 생성
                    feedback = analyzer.generate_ai_feedback(business_plan_text)

                    if feedback:
                        # 피드백 표시
                        st.header("💡 투자 심층 분석 결과")
                        st.markdown(feedback)

                        st.markdown("---")

                        # 점수 추출 및 시각화
                        st.header("📊 다차원 투자 평가")
                        scores = analyzer.parse_detailed_scores(feedback)

                        if scores:
                            analyzer.visualize_scores(scores)
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
    st.caption("Advanced Investment Analysis Platform powered by Streamlit, OpenAI GPT-4, PyMuPDF, Plotly")

if __name__ == "__main__":
    main()