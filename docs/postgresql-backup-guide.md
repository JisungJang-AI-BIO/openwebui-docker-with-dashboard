# PostgreSQL DB 백업 가이드

## 환경 정보
- PostgreSQL: Docker 컨테이너 (`openwebui-postgres`)
- 볼륨: Docker named volume (`openwebui_pgdata`)
- 접속: `localhost:5435`

## 1. 수동 백업 (pg_dump)

### 전체 DB 백업
```bash
docker exec openwebui-postgres pg_dump -U openwebui_admin -d openwebui -F c -f /tmp/openwebui_backup.dump
docker cp openwebui-postgres:/tmp/openwebui_backup.dump ./backups/openwebui_backup_$(date +%Y%m%d_%H%M%S).dump
```

### SQL 텍스트 형식 백업
```bash
docker exec openwebui-postgres pg_dump -U openwebui_admin -d openwebui > ./backups/openwebui_backup_$(date +%Y%m%d_%H%M%S).sql
```

## 2. 복원

### custom format (.dump) 복원
```bash
# DB 재생성 후 복원
docker exec openwebui-postgres dropdb -U openwebui_admin openwebui
docker exec openwebui-postgres createdb -U openwebui_admin openwebui
docker cp ./backups/openwebui_backup.dump openwebui-postgres:/tmp/openwebui_backup.dump
docker exec openwebui-postgres pg_restore -U openwebui_admin -d openwebui /tmp/openwebui_backup.dump
```

### SQL 텍스트 형식 복원
```bash
docker exec openwebui-postgres dropdb -U openwebui_admin openwebui
docker exec openwebui-postgres createdb -U openwebui_admin openwebui
docker exec -i openwebui-postgres psql -U openwebui_admin -d openwebui < ./backups/openwebui_backup.sql
```

## 3. 원클릭 백업 스크립트

`backup_db.sh` 사용:
```bash
./backup_db.sh
```

## 4. Docker named volume 직접 백업

컨테이너가 내려간 상태에서 볼륨 전체를 tar로 백업:
```bash
docker run --rm -v openwebui-dashboard_openwebui_pgdata:/data -v $(pwd)/backups:/backup alpine tar czf /backup/pgdata_volume_$(date +%Y%m%d).tar.gz -C /data .
```

## 5. 주의사항

- 백업 파일은 `backups/` 디렉토리에 저장 (.gitignore에 포함됨)
- 운영 DB 백업 시에는 `--no-owner` 옵션 고려 (소유자 차이 대응)
- Windows 재부팅 전에 백업하는 습관을 권장
