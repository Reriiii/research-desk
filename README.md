# LangGraph Research Agent

Research agent đa bước xây dựng bằng LangGraph, OpenAI và Tavily. Agent tự lập
kế hoạch, dùng vòng lặp ReAct để tìm kiếm và quan sát bằng chứng, đánh giá độ
đầy đủ, bổ sung phần còn thiếu và tạo báo cáo Markdown có nguồn tham khảo.

## Điểm nổi bật

- Lập kế hoạch nghiên cứu có cấu trúc gồm 3–6 bước.
- ReAct loop rõ ràng: Reason → Act (`web_search`) → Observe (`ToolMessage`).
- Thu thập bằng chứng web qua Tavily và giữ lại source URL.
- Đánh giá coverage trước khi viết báo cáo cuối.
- Tự nghiên cứu bổ sung tối đa 2 lần khi evidence chưa đủ.
- Giới hạn tối đa 5 vòng gọi tool cho mỗi bước để tránh loop vô hạn.
- Ba cách sử dụng: Textual TUI, FastAPI REST API và CLI.
- Correlation bằng `run_id` xuyên suốt state, log, API và AgentOps.
- Theo dõi OpenAI request ID, token usage, latency và stack trace.

## Kiến trúc

[![LangGraph Research Agent architecture](./architecture.visual-check.1440x900.light.png)](./architecture.html)

- [Mở architecture viewer tương tác](./architecture.html)
- [Xem JSON specification](./architecture.json)

Luồng chính:

```text
User → TUI / REST / CLI → Planner → ReAct Research Loop → Evaluator → Writer
                                      ├── OpenAI reasoning
                                      ├── Tavily action
                                      └── ToolMessage observation
```

Sơ đồ và viewer controls sử dụng English để thuận tiện chia sẻ trong tài liệu
kỹ thuật và repository công khai.

## Quy trình agent

1. `planner` chuyển câu hỏi thành 3–6 research steps.
2. `react_agent` reasoning nội bộ để xác định evidence còn thiếu.
3. Khi cần hành động, model phát tool call và node `act` gọi `web_search`.
4. Kết quả được đưa về dưới dạng `ToolMessage` để model Observe và lặp lại.
5. Khi đủ evidence, `save_research` lưu note và chuyển sang bước tiếp theo.
6. `evaluator` kiểm tra độ đầy đủ; `retry_planner` tạo bước bổ sung nếu cần.
7. `writer` tổng hợp báo cáo cuối chỉ từ evidence đã thu thập.

ReAct reasoning không được xuất ra dưới dạng chain-of-thought. Agent chỉ trả về
kết luận, evidence và source URL; phần reasoning riêng tư vẫn nằm trong model.

## Yêu cầu

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- OpenAI API key
- Tavily API key
- AgentOps API key nếu muốn remote tracing

## Cài đặt

```powershell
git clone https://github.com/Reriiii/langgraph-research-agent.git
Set-Location langgraph-research-agent
uv sync --frozen
Copy-Item .env.example .env
```

Cấu hình `.env`:

```dotenv
MODEL=gpt-5-mini
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key
AGENTOPS_API_KEY=your-agentops-api-key
LOG_LEVEL=INFO
```

| Biến | Bắt buộc | Mục đích |
|---|---:|---|
| `MODEL` | Có | OpenAI model dùng cho planner, ReAct agent, evaluator và writer |
| `OPENAI_API_KEY` | Có | Xác thực OpenAI API |
| `TAVILY_API_KEY` | Có | Web search cho evidence bên ngoài |
| `AGENTOPS_API_KEY` | Không | Trace replay và LLM spans trên AgentOps |
| `OPENAI_PROJECT` | Không | Chọn rõ OpenAI project để đối chiếu usage |
| `LOG_LEVEL` | Không | Mức log; mặc định `INFO` |

Không commit `.env` hoặc API key vào repository.

## Chạy TUI

```powershell
uv run python tui.py
```

Nhập câu hỏi rồi nhấn `Enter` hoặc chọn **Research**.

| Phím tắt | Chức năng |
|---|---|
| `Enter` | Bắt đầu research |
| `Ctrl+F` | Focus ô nhập câu hỏi |
| `Ctrl+K` | Xóa kết quả hiện tại |
| `Ctrl+Q` | Thoát TUI |

Ví dụ prompt:

```text
What are the three main benefits of solar energy? Use reliable sources and include URLs.
```

## Chạy REST API

```powershell
uv run python main.py
```

Sau khi server khởi động:

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>
- Research endpoint: `POST /research`

Ví dụ request:

```powershell
$body = @{
    query = "What are the three main benefits of solar energy? Use reliable sources."
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/research" `
    -ContentType "application/json" `
    -Body $body
```

Response:

```json
{
  "run_id": "a1b2c3d4e5f6",
  "final_report": "# Research report...",
  "research_complete": true,
  "evaluation": "Reason: ..."
}
```

## Chạy CLI mẫu

```powershell
uv run python run.py
```

Query mẫu hiện được khai báo trong `run.py`.

## Observability

### Local logs

Ứng dụng ghi rotating log vào `logs/research-agent.log`. Mỗi entry chứa
`run_id` và có thể bao gồm node, latency, OpenAI request ID, model thực tế,
token usage, tool call và stack trace.

Theo dõi realtime bằng PowerShell:

```powershell
Get-Content .\logs\research-agent.log -Wait
```

Lọc một run cụ thể:

```powershell
Select-String -Path .\logs\research-agent.log -Pattern "run_id=a1b2c3d4e5f6"
```

Log file xoay vòng ở 5 MB và giữ tối đa 3 bản cũ.

### AgentOps

Khi `AGENTOPS_API_KEY` tồn tại, mỗi lần chạy được gửi thành một trace
`research-agent` riêng, gắn tag `run_id` và nguồn gọi `tui`, `api` hoặc `cli`.
Dashboard URL được ghi trong local log dưới event `agentops_trace_started`.

AgentOps được dùng cho tracing, latency, token/cost visibility và replay. Các
quality evaluation định lượng như correctness, faithfulness hoặc regression
threshold nên được triển khai thêm bằng một eval framework chuyên dụng.

## Kiểm thử

Test suite mock toàn bộ OpenAI, Tavily và AgentOps; chạy test không phát sinh
request hoặc chi phí external API.

```powershell
uv run python -m unittest discover -v
```

Kiểm tra compile:

```powershell
uv run python -m compileall -q app main.py run.py tui.py tests
```

## Cấu trúc project

```text
.
├── app/
│   ├── agents/          # Planner, ReAct loop, evaluator, retry, writer
│   ├── api/             # FastAPI request/response routes
│   ├── graph/           # AgentState và LangGraph topology
│   ├── tools/           # Tavily web search tool
│   ├── logging_config.py
│   ├── observability.py # AgentOps initialization và trace lifecycle
│   ├── main.py          # FastAPI application
│   └── tui.py           # Textual application
├── tests/               # Unit, graph, API, TUI và observability tests
├── architecture.html    # Interactive architecture viewer
├── architecture.json    # Archify source specification
├── main.py              # API entrypoint
├── tui.py               # TUI entrypoint
└── run.py               # CLI example
```

## Lưu ý vận hành

- Một full research run có thể thực hiện nhiều OpenAI và Tavily requests.
- Theo dõi token usage và latency bằng local log hoặc AgentOps trước khi chạy
  workload lớn.
- Không đưa nội dung bí mật vào query vì query preview và trace metadata có thể
  được ghi phục vụ debugging.
- AgentOps là optional; nếu thiếu key, workflow vẫn chạy với local logging.
