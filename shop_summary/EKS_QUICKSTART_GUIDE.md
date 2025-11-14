# EKS + Airflow 벡터 DB 빠른 시작 가이드

> AWS EKS + Airflow 환경에서 로컬 벡터 DB (Chroma + EFS) 구축하기

**작성일**: 2025-11-14
**대상**: 월 2회 배치 실행 (1일, 15일), 매장 2,000개+ 처리

---

## 🎯 왜 EFS + 로컬 벡터 DB인가?

### 비용 비교 (연간)

| 옵션 | 비용 | 절감액 |
|------|------|--------|
| Pinecone | $840 | - |
| Qdrant Cloud | $300 | - |
| **Chroma + EFS** | **$0.12** | **$839.88** 🎉 |

### 핵심 이점

- ✅ **거의 무료** (연간 $0.12)
- ✅ **98.9% 유휴 시간에 과금 없음**
- ✅ **외부 의존성 없음** (장애 위험 제거)
- ✅ **2배 빠른 검색** (Pod 내부 I/O)
- ✅ **Multi-AZ 고가용성** (EFS 네이티브)

---

## 📋 3단계 구축 가이드

### Step 1: EFS 생성 및 PersistentVolume 설정 (1시간)

#### 1-1. EFS 파일시스템 생성

```bash
# AWS CLI로 EFS 생성
aws efs create-file-system \
  --creation-token llm-poc-vector-db \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=llm-poc-vector-db \
  --region us-east-1

# 출력에서 FileSystemId 기록 (예: fs-0123abcd)
```

#### 1-2. EFS 마운트 타겟 생성 (각 AZ마다)

```bash
# VPC 서브넷 확인
kubectl get nodes -o wide

# 각 AZ의 서브넷에 마운트 타겟 생성
aws efs create-mount-target \
  --file-system-id fs-0123abcd \
  --subnet-id subnet-xxxxx \
  --security-groups sg-xxxxx  # EKS Worker Node SG 사용
```

#### 1-3. EFS CSI Driver 설치

```bash
# Helm으로 설치 (권장)
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update

helm install aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/EFSCSIDriverRole

# 설치 확인
kubectl get pods -n kube-system | grep efs-csi
```

#### 1-4. PersistentVolume 및 PVC 생성

```yaml
# k8s/vector-db-pv.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: vector-db-pv
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: efs-sc
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123abcd  # 실제 EFS ID로 교체

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vector-db-pvc
  namespace: airflow  # Airflow가 실행되는 네임스페이스
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 1Gi
```

```bash
# 적용
kubectl apply -f k8s/vector-db-pv.yaml

# 확인
kubectl get pv,pvc -n airflow
# NAME                           STATUS   VOLUME          CAPACITY   ACCESS MODES
# persistentvolumeclaim/vector-db-pvc   Bound    vector-db-pv   1Gi        RWX
```

---

### Step 2: Airflow DAG 작성 (2시간)

#### 2-1. 기본 DAG 구조

```python
# dags/shop_summary_batch_dag.py
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['alerts@company.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'shop_summary_batch',
    default_args=default_args,
    description='매장 요약문 생성 배치',
    schedule_interval='0 2 1,15 * *',  # 매월 1일, 15일 오전 2시
    start_date=days_ago(1),
    catchup=False,
    tags=['llm', 'batch', 'rag'],
)

# Volume 설정 (공통)
volume_config = {
    'persistentVolumeClaim': {
        'claimName': 'vector-db-pvc'
    }
}

volume_mount = {
    'name': 'vector-db',
    'mountPath': '/data/vector_db'
}
```

#### 2-2. Task 정의

```python
# Task 1: 초기화 (S3에서 복원, 첫 실행 시만)
init_task = KubernetesPodOperator(
    task_id='init_vector_db',
    name='init-vector-db',
    namespace='airflow',
    image='your-repo/shop-summary:latest',
    cmds=['python', '-c'],
    arguments=['''
import os
import boto3

if not os.path.exists("/data/vector_db/chroma_db"):
    print("🔄 S3에서 벡터 DB 복원...")
    s3 = boto3.client("s3")
    s3.download_file(
        "your-bucket",
        "vector-db-backups/latest/chroma_db.tar.gz",
        "/tmp/chroma_db.tar.gz"
    )
    os.system("tar -xzf /tmp/chroma_db.tar.gz -C /data/vector_db/")
    print("✅ 복원 완료")
else:
    print("✅ 기존 벡터 DB 사용")
    '''],
    volumes=[volume_config],
    volume_mounts=[volume_mount],
    is_delete_operator_pod=True,
    get_logs=True,
    dag=dag,
)

# Task 2~4: 카테고리별 요약문 생성
categories = [
    'fine_dining_and_susi_omakase',
    'low_to_mid_price_dining',
    'waiting_hotplace'
]

category_tasks = []
for category in categories:
    task = KubernetesPodOperator(
        task_id=f'generate_{category}',
        name=f'generate-{category}',
        namespace='airflow',
        image='your-repo/shop-summary:latest',
        cmds=['papermill'],
        arguments=[
            f'/app/shop_summary/{category}/main_rag.ipynb',
            f'/tmp/{category}_output.ipynb',
            '-p', 'MODE', 'multi',
            '-p', 'VECTOR_DB_PATH', '/data/vector_db/chroma_db',
        ],
        volumes=[volume_config],
        volume_mounts=[volume_mount],
        resources={
            'request_memory': '2Gi',
            'request_cpu': '1',
            'limit_memory': '4Gi',
            'limit_cpu': '2',
        },
        env_vars={
            'GOOGLE_APPLICATION_CREDENTIALS': '/secrets/gcp-key.json'
        },
        is_delete_operator_pod=True,
        get_logs=True,
        dag=dag,
    )
    category_tasks.append(task)

# Task 5: S3 백업
backup_task = KubernetesPodOperator(
    task_id='backup_to_s3',
    name='backup-to-s3',
    namespace='airflow',
    image='your-repo/shop-summary:latest',
    cmds=['python', '-c'],
    arguments=['''
import os
import boto3
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# 압축
os.system(f"tar -czf /tmp/chroma_backup_{timestamp}.tar.gz -C /data/vector_db chroma_db/")

# S3 업로드
s3 = boto3.client("s3")
s3.upload_file(
    f"/tmp/chroma_backup_{timestamp}.tar.gz",
    "your-bucket",
    f"vector-db-backups/{timestamp}/chroma_db.tar.gz"
)

# latest 링크 갱신
s3.copy_object(
    CopySource={"Bucket": "your-bucket", "Key": f"vector-db-backups/{timestamp}/chroma_db.tar.gz"},
    Bucket="your-bucket",
    Key="vector-db-backups/latest/chroma_db.tar.gz"
)

print(f"✅ S3 백업 완료: {timestamp}")
    '''],
    volumes=[volume_config],
    volume_mounts=[volume_mount],
    is_delete_operator_pod=True,
    get_logs=True,
    dag=dag,
)

# Task 의존성
init_task >> category_tasks >> backup_task
```

---

### Step 3: Docker 이미지 빌드 및 배포 (1시간)

#### 3-1. Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    git \
    curl \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드
COPY shop_summary/ /app/shop_summary/

CMD ["python", "-c", "print('Ready')"]
```

#### 3-2. requirements.txt

```txt
google-cloud-aiplatform
google-genai
chromadb
python-dotenv
papermill
boto3
```

#### 3-3. 빌드 및 푸시

```bash
# Docker 이미지 빌드
docker build -t your-repo/shop-summary:latest .

# AWS ECR 푸시 (예시)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker tag your-repo/shop-summary:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/shop-summary:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/shop-summary:latest
```

---

## 🧪 테스트 및 검증

### 단일 카테고리 테스트

```bash
# Airflow UI에서 DAG 수동 트리거
# 또는 CLI로 실행
airflow dags trigger shop_summary_batch

# 로그 확인
kubectl logs -n airflow -l airflow-component=worker --tail=100
```

### EFS 데이터 확인

```bash
# 테스트 Pod 실행
kubectl run -it --rm debug --image=busybox --restart=Never -n airflow -- sh

# Pod 내부에서
ls -lh /data/vector_db/chroma_db/
# fine_dining_examples/
# low_to_mid_price_dining_examples/
# waiting_hotplace_examples/
```

---

## 📊 모니터링

### CloudWatch Logs 수집

```yaml
# k8s/fluentd-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: airflow
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/generate-*.log
      tag airflow.*
    </source>

    <match airflow.**>
      @type cloudwatch_logs
      log_group_name /aws/eks/shop-summary-batch
      log_stream_name ${tag}
    </match>
```

### EFS 메트릭 (CloudWatch)

```bash
# AWS Console → CloudWatch → Metrics → EFS
# 모니터링 지표:
# - ClientConnections (Pod 연결 수)
# - DataReadIOBytes (읽기 바이트)
# - DataWriteIOBytes (쓰기 바이트)
# - PercentIOLimit (IOPS 사용률)
```

---

## ⚠️ 문제 해결

### EFS 마운트 실패

```bash
# 증상: Pod가 Pending 상태
kubectl describe pod <pod-name> -n airflow
# Events: "MountVolume.SetUp failed for volume"

# 해결:
1. Security Group 확인
   - EKS Worker Node SG에 NFS (포트 2049) 허용
2. EFS 마운트 타겟 확인
   - 각 AZ에 마운트 타겟 있는지 확인
3. EFS CSI Driver 재시작
   kubectl rollout restart deployment efs-csi-controller -n kube-system
```

### 벡터 DB 데이터 손실

```bash
# S3에서 백업 복원
aws s3 cp s3://your-bucket/vector-db-backups/latest/chroma_db.tar.gz .

# EFS 마운트된 EC2에서 복원
tar -xzf chroma_db.tar.gz -C /mnt/efs/
```

### 메모리 부족

```yaml
# Pod 리소스 증가
resources:
  request_memory: '4Gi'  # 2Gi → 4Gi
  request_cpu: '2'       # 1 → 2
  limit_memory: '8Gi'    # 4Gi → 8Gi
  limit_cpu: '4'         # 2 → 4
```

---

## 🎯 체크리스트

### 초기 설정
- [ ] EFS 파일시스템 생성
- [ ] EFS CSI Driver 설치
- [ ] PV/PVC 생성 및 바인딩 확인
- [ ] S3 버킷 생성 (백업용)
- [ ] IAM Role 설정 (Pod → S3 접근)

### Airflow DAG
- [ ] shop_summary_batch_dag.py 작성
- [ ] Volume Mount 설정 확인
- [ ] GCP 인증 키 Secret 생성
- [ ] 단일 카테고리 테스트
- [ ] 3개 카테고리 전체 테스트

### 운영
- [ ] CloudWatch Logs 수집 설정
- [ ] EFS 메트릭 모니터링
- [ ] S3 Lifecycle Policy 설정 (30일 보관)
- [ ] 알림 설정 (DAG 실패 시 이메일)
- [ ] 재해 복구 테스트 (S3 백업 → EFS 복원)

---

## 💡 베스트 프랙티스

### 1. 백업 전략
- 배치 완료 후 즉시 S3 백업
- 날짜별 버전 관리 (30일 보관)
- 월 1회 전체 백업 검증

### 2. 리소스 최적화
- Pod 리소스 Request: 실제 사용량 × 1.2
- Pod 리소스 Limit: Request × 2
- EFS Provisioned Throughput: 처음엔 불필요 (Bursting 사용)

### 3. 보안
- EFS 암호화 필수 (at-rest)
- IAM Role 최소 권한 원칙
- GCP 인증 키는 K8s Secret으로 관리

### 4. 비용 최적화
- EFS IA (Infrequent Access): 30일 후 자동 전환 설정
- S3 Intelligent-Tiering 사용
- CloudWatch Logs 보관 기간: 7일

---

## 📚 참고 자료

- **전체 비용 분석**: `BATCH_PIPELINE_COST_ANALYSIS.md`
- **Hybrid Search 적용**: `HYBRID_SEARCH_MIGRATION_GUIDE.md`
- **네이버 사례**: `NAVER_PLACE_AI_AGENT_CASE_STUDY.md`

### AWS 공식 문서
- [EFS CSI Driver](https://github.com/kubernetes-sigs/aws-efs-csi-driver)
- [EFS 가격](https://aws.amazon.com/efs/pricing/)
- [Airflow on EKS](https://aws.amazon.com/blogs/containers/running-apache-airflow-on-amazon-eks/)

---

**작성자**: Claude Code
**업데이트**: 2025-11-14
**예상 구축 시간**: 4~5시간
**연간 비용**: $0.12
