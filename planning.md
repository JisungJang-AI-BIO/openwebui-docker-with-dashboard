# Open WebUI Dashboard Project Plan 
(Open WebUI 대시보드 프로젝트 기획안)

## 1. Project Overview (프로젝트 개요)
This project aims to develop a real-time dashboard to monitor and analyze the usage of an Open WebUI instance served on an on-premise server. The development environment will be set up on WSL (Ubuntu) to closely mirror the production environment.
(본 프로젝트는 사내 온프레미스 서버에서 운영 중인 Open WebUI의 사용 현황을 모니터링하고 분석하기 위한 실시간 대시보드를 개발하는 것을 목표로 합니다. 개발 환경은 WSL(Ubuntu) 상에 구축하여 실제 운영 환경과 최대한 유사하게 구성합니다.)

## 2. Environment Setup (환경 설정)
### 2.1. Infrastructure (인프라)
- **OS**: Windows (Host), WSL 2 Ubuntu (Guest)
- **Python Environment**: Conda (Miniforge), Python 3.11
- **Path**: Project located at `D:/openwebui-dashboard`, Conda prefix at `/mnt/d/conda/...`
(운영체제는 윈도우 기반의 WSL2 Ubuntu를 사용하며, Python 3.11 기반의 Conda 환경을 D 드라이브에 구성합니다.)

### 2.2. Database (데이터베이스)
- **Engine**: PostgreSQL with `pgvector` extension (Latest version)
- **Security**: 
    - Database and disk encryption enabled.
    - Separation of duties: `DB Admin` vs `Audit Admin`.
- **Connection**: Dashboard connects directly to this PostgreSQL instance.
(데이터베이스는 최신 버전의 PostgreSQL과 pgvector 확장을 사용합니다. 보안을 위해 DB 및 디스크 암호화를 적용하고, 관리자 계정과 감사(Audit) 계정을 분리하여 운영합니다.)

## 3. Dashboard Features (대시보드 기능)
The dashboard will be a modern Single Page Application (SPA) built with **React** and **FastAPI**, offering granular multi-user support and high customization.
(Streamlit의 한계를 극복하기 위해 React(Frontend)와 FastAPI(Backend) 분리 아키텍처를 채택하여 멀티유저 지원 및 높은 커스터마이징을 제공합니다.)

### 3.1. Architecture
- **Frontend**: React (Vite), TailwindCSS, Recharts/Nivo (Visualization).
- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic.
- **Auth**: JWT based authentication (User/Admin roles).

### 3.2. Core Metrics
1.  **Creator Analysis (생성자 분석)**:
    - Identify creators of models and workspaces.
2.  **Usage Trends (사용량 추이)**:
    - Interactive time-series charts (Daily/Weekly/Monthly).
3.  **Feedback Metrics (피드백 지표)**:
    - Like/Dislike ratios with drill-down capabilities.
4.  **Feedback Comments (피드백 코멘트)**:
    - Searchable and filterable data grid of user feedback.

## 4. Security & Deployment (보안 및 배포)
- **Secrets Management**: `.env` managed secrets.
- **Dockerization**: 
    - `frontend`: Nginx serving React static build.
    - `backend`: Uvicorn serving FastAPI.
- **Multi-user Support**:
    - **Role Based Access Control (RBAC)**: Admin vs Viewer.
    - **Session Management**: Secure HTTP-only cookies/JWT.

## 5. Directory Structure (폴더 구조)
```
d:/openwebui-dashboard/
├── docker-compose.yml      # Postgres, Backend, Frontend
├── .env                    # Shared Secrets
├── README.md
├── planning.md
├── backend/                # FastAPI Application
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/               # React Application (Vite)
    ├── src/
    ├── Dockerfile
    └── package.json
```
