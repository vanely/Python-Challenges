# Design 1 — Loan Status Integration

> **Prompt:** "When a loan's status changes in Encompass, update our internal system and notify the loan officer."

Encompass is the mortgage software where loans are processed (application → underwriting → approval → closing). The bank's other systems (its internal database, reporting, the CRM) need to know when a loan moves forward, and the loan officer wants a heads-up.

---

## Interview script (your 25-minute outline)

1. **Clarify** (3 min): the questions below.
2. **Estimate scale** (1 min): it's small, so say so.
3. **Draw the happy path** (5 min): webhook → queue → worker → database → notification.
4. **Failure paths** (8 min): duplicates, out-of-order events, a vendor outage, bad messages, missed webhooks.
5. **Security and audit** (4 min).
6. **Tradeoffs and alternatives** (4 min).

---

## 1. Clarifying questions (ask these first)

| Question | Why it matters |
|---|---|
| Which status changes matter? All of them, or key milestones (Approved, Clear to Close, Funded)? | Decides how much we process and how many notifications we send. |
| How fast must the internal system update? Seconds? Minutes? | If minutes are fine, polling alone might be enough. |
| How is the loan officer notified (email, Teams, text)? | Picks the notification tool. |
| Does Encompass offer webhooks for our account, and is there a rate limit on its API? | Decides push vs. pull, and how fast we can call it. |
| Is the internal system our own Postgres database, or another vendor? | Decides how we "update" it. |
| Audit requirements: how long do we keep records of every change? | Banks often keep records for years. |

**Assumptions I'll state if they don't answer:**
- Webhooks are available.
- Updates within about a minute are fine.
- Notifications go by email and Teams.
- The internal system is our Postgres on RDS.

---

## 2. Scale estimate (a senior move: do the math, then say what it means)

- Leader Bank closed about **$3.3B** in residential loans in 2025, across a bit more than **6,200** closed loans (about **$530K** average). Applications are higher than closings.
- Each loan may fire dozens to a couple of hundred change events over its life, since Encompass fires an event on many field changes, not just status.
- That's roughly **1 million events a year**, or a few per minute on average, with **spikes of 10x or more** when rates drop and applications surge.

**What that means:** this is *not* a big-data problem. **The hard part is correctness**: no lost updates, no double notifications, a clean audit trail. Saying this shows judgment.

---

## 3. The design

```
                                   (safety net, every 15 min)
                                 +---------------------------+
                                 |  Reconciliation poller    |
                                 |  (EventBridge Scheduler   |
                                 |   -> Lambda)              |
                                 +-------------+-------------+
                                               | "loans changed since last check"
                                               v
 Encompass --webhook--> API Gateway --> Receiver Lambda --> SQS queue --> Worker Lambda
                                          |  1. verify signature            | 1. idempotency check
                                          |  2. save raw payload to S3      | 2. fetch CURRENT loan state
                                          |  3. enqueue, reply 200 fast     |    from Encompass API
                                          |                                  | 3. update Postgres (one transaction)
                                          |                                  | 4. publish "LoanStatusChanged"
                                          v                                  v
                                     S3 (audit,                       SNS topic / EventBridge
                                     Object Lock)                            |
                                                                +------------+------------+
                                                                v                         v
                                                       Notify queue (SQS)         Other consumers
                                                                |                 (reporting, CRM)
                                                                v
                                                       Notifier Lambda --> SES email / Teams
                          SQS queues each have a DLQ  +  CloudWatch alarms on DLQ depth
```

### The happy path, step by step

1. **A loan officer clicks "Approved" in Encompass.** Encompass sends a webhook (an HTTP POST) to our URL. The payload is usually small, often just the loan ID, event type, and timestamp.

2. **API Gateway** receives it and passes it to the **Receiver Lambda**, which does only three quick things:
   - **Verifies the signature** (an HMAC header) to prove the request really came from Encompass.
   - **Saves the raw payload to S3.** This gives us an untouched copy for audit and debugging, and lets us replay events later.
   - **Puts a small message on an SQS queue** (`{event_id, loan_id, event_time}`) and immediately returns `200 OK`.

   *Why so little?* Webhook senders expect a fast reply. If we're slow, they may time out and send it again, or stop sending. Doing the real work later, off a queue, keeps the front door fast.

3. **The Worker Lambda** picks up the message from SQS and:
   - **Checks idempotency:** "have I already processed `event_id`?" If yes, it deletes the message and stops (section 4).
   - **Fetches the loan's current state from the Encompass API**, using an OAuth token whose secret lives in Secrets Manager. It treats Encompass as the **source of truth** and doesn't trust the webhook payload's details.
   - **Updates Postgres in one database transaction:**
     - Updates the `loans` row.
     - Inserts a row into `loan_status_history` (who, what, when).
     - Records the `event_id` as processed.
   - **Publishes a "LoanStatusChanged" event** to SNS or EventBridge for anyone who cares.

4. **The Notifier** (its own queue and Lambda) sends the email or Teams message to the loan officer.

5. **The reconciliation poller** runs every 15 minutes. It asks Encompass "which loans changed since my last checkpoint?" and puts any it finds on the same queue. Anything the webhooks missed gets caught here, and idempotency makes it harmless if the webhook already handled it.

---

## 4. The deep dives (where you show seniority)

### 4a. Duplicates: idempotency

**Why duplicates happen:**
- Webhooks are delivered **at least once**, and vendors retry if they didn't get a fast `200`.
- SQS Standard is also at-least-once.
- The reconciliation poller re-discovers changes the webhook already handled.

**The fix:** every event has an ID. Record it the moment it's processed, and skip it if it shows up again.

**Where to record it, and the subtle part:**
```sql
-- A table whose PRIMARY KEY makes duplicates impossible
CREATE TABLE processed_events (
    event_id     TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

BEGIN;
  INSERT INTO processed_events (event_id) VALUES ('evt-789')
      ON CONFLICT (event_id) DO NOTHING;   -- if 0 rows inserted -> already done, ROLLBACK & stop
  UPDATE loans SET status = 'Approved', updated_at = now() WHERE loan_id = '123';
  INSERT INTO loan_status_history (...) VALUES (...);
COMMIT;
```
Putting the idempotency record **in the same transaction** as the update means both happen or neither does.

If you recorded "processed" in a separate system (like DynamoDB) *after* the update, a crash between the two steps would cause a double-process on retry. Recording it *before* the update could lose the update if the update then fails.

| Option | Pros | Cons |
|---|---|---|
| **Same Postgres transaction** (above) | Atomic with the business update; simplest correct answer | Adds a little load to the main database |
| **DynamoDB conditional write** (`attribute_not_exists(event_id)`) | Very fast; built-in TTL cleans up old keys | Not atomic with the Postgres update, so you need an "in progress → done" status to handle crashes |
| **SQS FIFO deduplication** | Free and built in | Only covers a **5-minute window**, and only duplicates *sent to SQS*. It doesn't catch the poller re-finding an old change |

**Notifications need their own idempotency.** Use a key like `event_id + recipient + "email"` so a retried notifier doesn't email the loan officer twice. Duplicate notifications are what users actually notice.

### 4b. Out-of-order events

Two quick changes ("Conditionally Approved" then "Approved") can arrive in reverse order. If we blindly apply each one, the loan ends up stuck on the *older* status.

| Approach | How | Tradeoff |
|---|---|---|
| **Re-fetch current state** (my pick) | Treat the event as just a "something changed" nudge, and always read the latest loan from the API | Simple and always correct; costs one API call per event |
| **Compare timestamps/versions** | Store `last_event_time` on the loan; ignore events older than it | No extra API call; depends on the vendor's timestamps being reliable |
| **SQS FIFO with `MessageGroupId = loan_id`** | Messages for the same loan are processed one at a time, in order | Guaranteed order per loan; lower throughput, and one stuck message blocks that loan's later updates |

### 4c. Failures and retries

| What fails | What happens | Why it's OK |
|---|---|---|
| Our worker crashes mid-processing | It never deleted the message, so after the **visibility timeout** it reappears and is retried | The DB transaction rolled back, so nothing is half-done |
| Encompass API returns 503 / 429 | The worker raises an error, and SQS redelivers with a delay. Inside the worker, retry 2–3 times with **exponential backoff + jitter** | The vendor gets breathing room; a 429's `Retry-After` header is respected |
| Encompass is down for 2 hours | Messages pile up safely in SQS (kept for 4 days by default, up to 14). A **circuit breaker** stops pointless calls | When it recovers, the queue drains on its own |
| One message is broken (bad data, a bug) | After N failed receives (say 5), SQS moves it to the **dead-letter queue** | One poison message can't block everything or retry forever |
| Our webhook endpoint was down | Encompass may give up retrying | The **reconciliation poller** catches up on its next run |

**Two settings to name:**
- **Visibility timeout** must be longer than the worker's maximum run time. Otherwise a slow-but-healthy worker's message gets handed to a *second* worker.
- **Lambda partial batch response** (`ReportBatchItemFailures`): if 1 of 10 messages in a batch fails, only that one is retried, not all 10.

**Protecting the vendor and our database:** cap the worker's **maximum concurrency**, e.g. at most 10 workers at once. During a mortgage spike, the queue absorbs the surge while we stay under Encompass's rate limit and Postgres's connection limit. **RDS Proxy** pools database connections.

### 4d. Audit and observability

- **Audit trail:**
  - Raw payloads in **S3 with Object Lock** (can't be altered).
  - `loan_status_history` rows record who, what, when, and the source event ID.
  - **CloudTrail** records who changed the infrastructure itself.
- **Correlation ID:** put `event_id` and `loan_id` on every log line in every Lambda. One search in **CloudWatch Logs Insights** then shows an event's whole journey.
- **Metrics and alarms:**
  - Queue depth and **age of the oldest message** (are we falling behind?)
  - **DLQ depth > 0** (alarm immediately)
  - Error rate
  - Encompass API latency
- **Don't log PII.** Log `loan_id`, never the borrower's name, SSN, or income.

### 4e. Security

- **Verify webhook signatures.** Also consider allowlisting the vendor's IP ranges if they publish them.
- **Least-privilege IAM:** each Lambda can touch only its own queue, table, and secret.
- **Secrets Manager** for the OAuth client secret, with rotation.
- **Encryption:** SQS, S3, and RDS encrypted with KMS; TLS on every connection.
- **Keep messages small:** just IDs. Sensitive loan details stay in Encompass and Postgres, not floating around in queues.
- Run workers **inside a VPC**, reaching AWS services through VPC endpoints.

---

## 5. Alternatives and tradeoffs (say at least two of these out loud)

| Decision | My choice | Alternative | Why I'd pick mine here |
|---|---|---|---|
| How to learn about changes | Webhooks + reconciliation poller | Polling only | Webhooks give speed; the poller gives completeness. Polling only is simpler and would be fine if minutes of delay are OK. |
| Buffer between systems | SQS | EventBridge / Kinesis | SQS is the simplest durable queue with built-in retries and DLQs. EventBridge if we need content-based routing to many targets; Kinesis is overkill at this volume. |
| Compute | Lambda | ECS / Fargate containers | Spiky, short tasks with no servers to manage. Containers if jobs run longer than 15 minutes or traffic is steady and heavy. |
| Fan-out | SNS topic → one SQS queue per consumer | The worker calls each consumer directly | Adding a new consumer (CRM, reporting) needs no change to the worker. A slow consumer can't slow down the others. |
| Idempotency store | Same Postgres transaction | DynamoDB | Atomic with the update, so there's nothing to reconcile. |
| Build vs. buy | Custom AWS code | An integration platform (MuleSoft, Boomi) | Platforms have ready-made connectors and visual flows, but cost license fees and are harder to test like code. Many banks use both: platforms for simple syncs, code for logic-heavy flows. |

---

## 6. Likely follow-up questions (and short answers)

- **"How would you test this?"**
  - Unit test the worker with a **fake Encompass client** (dependency injection, like Round 1, problem 8).
  - Integration tests against a sandbox Encompass instance.
  - Replay saved S3 payloads to reproduce bugs.
  - Test duplicates and out-of-order events on purpose.

- **"How do you deploy it safely?"**
  - Infrastructure as code (CloudFormation, CDK, or Terraform) so every environment is identical.
  - **Canary** deploy the Lambdas, watching error alarms.
  - Keep a **feature flag** for notifications.

- **"What if the loan officer complains they never got the email?"**
  - Search the logs by `loan_id`.
  - Check the notify queue's DLQ.
  - Check SES delivery and bounce events.
  - The correlation ID makes this a 2-minute check.

- **"How would you replay a day of events after fixing a bug?"**
  - Raw payloads are in S3. Re-enqueue them; idempotency skips anything already applied correctly.
  - For DLQ messages, use SQS **redrive** back to the main queue.

- **"What does it cost?"** At about a million events a year, Lambda, SQS, and SNS cost very little, likely dollars a month. The real costs are engineering time and the vendor's API fees.
