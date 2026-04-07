docker run -d -p 11235:11235 --name crawl4ai unclecode/crawl4ai:latest

docker run --name agent_postgres \
  -e POSTGRES_USER=agent \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=agent_db \
  -p 5432:5432 \
  -v ./postgres_data:/var/lib/postgresql \
  -d postgres:18

## 数据库初始化

运行初始化脚本创建表结构和索引：
```bash
uv run python init_db.py
```