# 📂 Easy-File-Utils

일상적인 파일 작업 및 관리를 위한 유용한 파이썬 유틸리티 모음입니다. 각 도구는 GUI(Tkinter) 기반으로 제작되어 누구나 쉽게 사용할 수 있습니다.

---

## 🛠️ 포함된 도구

### 1. [checkFileSize](./checkFileSize) - 폴더 용량 비교 도구
두 폴더(원본 ↔ 복사본)의 **파일 수**와 **전체 용량**을 빠르게 비교하여 데이터 무결성을 확인합니다.
- **주요 기능:** 엑셀 파일을 이용한 대량 경로 비교, 폴더 직접 선택, 결과를 CSV로 저장.
- **실행:** `python checkFileSize/check_file_size.py`

### 2. [xlsxTocsv](./xlsxTocsv) - Excel to CSV 변환기
Excel(.xlsx) 파일을 CSV(.csv) 파일로 일괄 변환하는 도구입니다.
- **주요 기능:** 단일 파일 또는 폴더 내 모든 엑셀 파일 변환, 시트 지정(이름/인덱스), 출력 인코딩(UTF-8 등) 설정.
- **실행:** `python xlsxTocsv/xlsxTocsv.py`

---

## 🚀 시작하기

### 1. 요구 사항
이 도구들은 Python 3.8 이상에서 원활하게 작동합니다.

### 2. 필수 라이브러리 설치
각 도구에서 공통적으로 사용하는 라이브러리를 설치합니다.

```bash
pip install pandas openpyxl
```

또는 `xlsxTocsv` 폴더 내의 `requirements.txt`를 사용할 수 있습니다.

```bash
pip install -r xlsxTocsv/requirements.txt
```

---

## 📖 사용 방법

1. 저장소를 클론하거나 다운로드합니다.
2. 사용하려는 도구의 디렉토리로 이동하거나 루트에서 해당 스크립트를 실행합니다.
3. 각 도구의 상세 사용법은 해당 폴더의 `README.md`를 참고하세요.

---

## 📄 라이선스
이 프로젝트는 개인 학습 및 도구 제작 목적으로 작성되었습니다.
