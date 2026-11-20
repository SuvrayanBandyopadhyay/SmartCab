# SmartCab — AI-Powered Employee Transport Assistant

An AI-powered shift-change assistant built for the MoveInSync campus case study. SmartCab allows employees to interact with their transport system through natural language, check their daily roster, explore alternative cab slots, and submit shift-change requests.

The system combines an LLM-driven conversational interface with a deterministic command interpreter and a background evaluator to ensure that transport policies and booking decisions are enforced by application code rather than the language model.

## 1. Overview

SmartCab provides a conversational interface for employees to interact with this system.

An employee can:
- Ask about their current transport roster.
- Check company transport policies.
- Explore available cab slots.
- Request a shift change using a specific time or slot.
- Request the nearest available time when their preferred slot is unavailable.
- Track requests through statuses such as PENDING, WAITLISTED, APPLIED, FAILED, and SUPERSEDED.

The application supports multiple companies with isolated employee data and company-specific policies.

## 2. Architecture

### High-level workflow

```text
              Employee
                  |
                  v
          Streamlit Frontend
                  |
                  v
             FastAPI
                  |
             JWT Auth
                  |
                  v
          AI Conversation Layer
                  |
                  v
        Structured Command Output
                  |
                  v
           CabLang Interpreter
                  |
          +-------+-------+
          |       |       |
        Roster  Policy   Requests
          |       |       |
          +-------+-------+
                  |
                  v
             PostgreSQL
                  |
                  v
          Background Evaluator
                  |
          +-------+-------+
          |               |
        APPLIED        WAITLISTED
          |               |
          v               v
      Roster Update   Re-evaluation
```

### Technology stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | Streamlit |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy |
| Authentication | JWT |
| LLM | Google Gemini |
| Command interpreter | CabLang |
| Containerization | Docker Compose |
| Testing | Pytest |

## 3. Design Decisions

### 3.1 The LLM 

The LLM is responsible for understanding natural language and maintaining conversational context.

It converts employee messages into structured responses containing:
- A response type.
- A natural-language message.
- A list of structured commands.

The LLM does not directly access the database, modify employee rosters, or make policy decisions.

The generated commands are passed to CabLang, which validates and executes them using application code.

This separation ensures that a confident but incorrect model response cannot directly change transport assignments.

### 3.2 CabLang

CabLang acts as the boundary between natural-language interaction and backend operations.

Supported commands include:

**Information queries**
- `CHECK COMPANY`
- `CHECK ROSTER`
- `CHECK POLICY`
- `CHECK CABS`
- `CHECK REQUESTS`
- `CHECK TIME HH:MM MARGIN`

**Shift-change requests**
- `REQUEST TIME HH:MM`
- `REQUEST TIME HH:MM NEAREST`
- `REQUEST SLOT SLOT_ID`

The interpreter validates commands and obtains the relevant employee and company context from the authenticated request.

The interpreter creates shift-change requests rather than directly modifying rosters. Actual changes are handled by the evaluator.

### 3.3 Authentication and company isolation

JWT authentication establishes the employee's identity and company membership.

The employee ID and company ID are obtained from the authenticated token, not from:
- User-provided chat messages.
- LLM-generated commands.
- Frontend request parameters.

Database queries are scoped using the authenticated employee and company context.

This prevents employees from accessing another company's roster or requests simply by changing an identifier in their input.

### 3.4 Company-specific policies

Each company has its own policy record. This policy record is stored in a json format.

The policy determines constraints such as:
- Maximum cab capacity.
- Request cut-off time.
- Whether overcapacity is permitted.
- Whether a manager's approval is required for a cut-off violation.

These rules are enforced in backend code rather than relying on LLM instructions.

### 3.5 Asynchronous request evaluation

Shift-change requests are created with a pending status.

A separate evaluator process periodically examines active requests and determines whether they can be applied.

Possible outcomes include:

| Status | Meaning |
|---|---|
| PENDING | Request is awaiting evaluation |
| WAITLISTED | Requested cab slot is currently full |
| APPLIED | Shift change has been successfully applied |
| FAILED | Request could not be processed |
| SUPERSEDED | Request has been replaced by a newer request |
| APPROVAL_REQUIRED | Request requires an approval decision |
| REJECTED | Request has been rejected |

A full cab does not automatically cause a request to be discarded. The request can remain WAITLISTED and be evaluated again when capacity becomes available.

### 3.6 Preventing conflicting requests

When a newer request is submitted for the same roster assignment, older active requests are marked SUPERSEDED.

The evaluator considers the latest active request, preventing an older request from being applied after a newer one has replaced it.

This provides protection against conflicting sequential requests.


### 3.7 Conversation history

Conversation history is maintained in application memory while the API process is running.

The most recent 10 messages are supplied as context to the LLM.

Persistent conversation storage was deliberately avoided because important transport changes and request decisions are already recorded in PostgreSQL.

This keeps the conversational layer simple without sacrificing the persistence of business operations.

## 4. Sample Data

The application includes two sample companies with different transport policies.

| Configuration | X Technologies | Y Solutions |
|---|---:|---:|
| Company ID | 1 | 2 |
| Maximum cab capacity | 4 | 6 |
| Cut-off period | 120 minutes | 90 minutes |
| Cab | X-101 | Y-101 |

The seed script creates:
- Two companies.
- Employee and manager accounts.
- Company-specific transport policies.
- Cabs and time slots.
- Initial roster assignments.


## 5. Running the Application

### Prerequisites

- Docker Desktop
- Docker Compose
- A Gemini API key for live LLM interaction

### Environment configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg://smartcab:smartcab_dev@db:5432/smartcab

JWT_SECRET=replace_with_a_secure_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```


### Start the application

From the project root:

```powershell
docker compose up -d --build
```

Docker Compose starts:
- PostgreSQL database.
- FastAPI backend.
- Background evaluator.

### Initialize sample data

For the initial setup:

```powershell
docker compose exec api python -m app.seed
```

**Warning:** The seed script drops and recreates the application's database tables. Running it again resets existing application data.

### Access the application

- Streamlit frontend: `http://localhost:8501`
- FastAPI backend: `http://localhost:8000`


## 6. Testing and Evaluation

The project includes an automated CabLang interpreter evaluation suite.

### Run the tests

```powershell
docker compose exec api python -m tests.test_interpreter
```

The test runner:
1. Loads the evaluation cases from the JSONL file.
2. Executes each command against the seeded database.
3. Compares actual results against expected results.
4. Records pass/fail status.
5. Measures individual execution times.
6. Reports total and average execution time.

### Evaluation dataset

The evaluation cases are stored in:

`tests/interpreter_cases.jsonl`

Each line follows the required JSONL structure:

```json
{
  "id": "TC01",
  "input": "CHECK COMPANY",
  "expected": {
    "name": "X Technologies"
  },
  "actual": null,
  "pass": null,
  "notes": "Verifies company information retrieval."
}
```

The evaluation set covers:
- Company and roster retrieval.
- Policy and cab information.
- Available time-slot queries.
- Exact-time shift-change requests.
- Nearest-slot selection.
- Invalid slot handling.
- Duplicate/current-slot request handling.
- Request creation and status retrieval.

The test runner records execution time in milliseconds for each case.

### Initial evaluation results

| Metric | Result |
|---|---:|
| Total test cases | 22 |
| Passed | 21 |
| Failed | 1 |
| Pass percentage | 95.45% |
| Average execution time | 15.730 ms |
| Fastest test | 3.639 ms |
| Slowest test | 52.354 ms |

The initial failure was TC06, where the expected number of available slots did not match the actual seeded data. The expected result was corrected to reflect the interpreter's actual availability query.

These figures measure interpreter and database execution, not end-to-end LLM response latency.

## 7. Trade-offs

### Deterministic interpreter instead of direct database tools

The LLM could have been given individual database functions. Instead, a structured command interface was chosen.

This adds a small interpretation layer but provides a clear boundary between model-generated intent and application-controlled operations.

### In-memory conversation history

Conversation history is not persisted across API restarts.

This reduces implementation complexity and avoids storing redundant conversational data. Important business changes remain persisted in PostgreSQL.

The trade-off is that conversational context is lost when the API process restarts.

### Background polling evaluator

The evaluator runs independently from the API and periodically checks pending requests.

This makes request processing independent of the employee's chat session and allows WAITLISTED requests to be reconsidered.

The trade-off is that processing is not instantaneous and depends on the evaluator's polling interval.
