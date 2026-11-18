# Design 3 — Troubleshooting: "The VP Says the App Crashes"

> **Prompt (a real question Shashi has asked):** "A VP calls you and says the app isn't working. It crashes when he tries to open it. Assume he knows how to use the app. What do you ask him?"

Shashi is checking whether you **stay calm, ask sharp questions, protect users first, and work methodically** instead of guessing. There's no single right answer. The *order* of your thinking is what gets graded.

---

## Interview script

1. Show you'll **take it seriously and stay calm**. This is a VP, but treat it like any other incident.
2. Ask **clarifying questions** to *scope* the problem (section 1).
3. **Check whether it's bigger than one person** (section 2).
4. **Stop the bleeding first** (roll back or turn off a feature flag), *then* find the root cause (section 3).
5. **Communicate** throughout, and **prevent it from happening again** (section 4).

The one-line version to say at the start:
> "First I'd figure out how big the problem is: just him, or everyone? Then what changed recently. If it's widespread, I'd fix it for users first, usually with a rollback, and dig for the root cause after."

---

## 1. Questions to ask the VP

Keep it short and respectful. He's busy and frustrated.

| Question | What the answer tells you |
|---|---|
| **Which app?** Mobile, web, or an internal tool? | Points you at the right logs and team |
| **What device and version?** iPhone or Android, which OS? Which browser? Which app version? | A fresh OS update or old app version is a classic cause |
| **What exactly happens?** It closes instantly, a white screen, an error message? Can you send a screenshot? | "Closes instantly" usually means a crash on startup; an error message is a direct clue |
| **When did it start?** Did it work this morning or yesterday? | Lets you line it up with recent deploys or changes |
| **Does it happen every time?** | Every time means easier to reproduce; sometimes means timing, network, or specific data |
| **Does it work anywhere else?** Another device, the website, Wi-Fi vs. cellular? | Separates "his device or account" from "the app" |
| **Did anything change on your end?** A new phone, an OS update, a password change, VPN? | Rules things in or out quickly |
| **Is anyone else on your team seeing it?** | The fastest way to check scope |

**What you'd say to him:**
> "Thanks, I'll look right now. Could you try it once on the website so we know if you're blocked? I'll update you within 30 minutes either way."

That gives him a workaround and a time you'll update him.

---

## 2. Scope it: one person, or everyone?

Check the data **while** you talk to people:

1. **Monitoring dashboards:** is the error rate or crash rate up for everyone?
   - **Mobile:** a crash-reporting tool (Firebase Crashlytics, Sentry) groups crashes by app version, OS, and device, with a stack trace.
   - **Backend:** CloudWatch metrics for the API, like 5xx error count, latency, and Lambda errors.
2. **Support channels:** any other tickets or Teams messages in the last hour?
3. **What changed?** This is the most useful question in all of incident response:
   - Did we **deploy** code or settings recently? (Check the deploy history.)
   - Did someone change infrastructure? (**CloudTrail** shows who changed what in AWS.)
   - Did a **vendor** change something, like an API update or an outage on their status page?
   - Did something **expire**? TLS certificates, OAuth client secrets, and API keys expiring are very common causes of "it suddenly broke."
   - Did Apple or Google release an **OS update**?

**Search the logs for errors** with a CloudWatch Logs Insights query:

```
fields @timestamp, @message
| filter @message like /ERROR|Exception/
| sort @timestamp desc
| limit 50
```

To see *when* errors started, count them per 5-minute bucket:

```
filter @message like /ERROR/
| stats count(*) as errors by bin(5m)
```

To follow **just the VP's session**, filter by his user ID or a correlation ID, never by personal details:

```
fields @timestamp, @message
| filter userId = "u-48213"
| sort @timestamp asc
```

---

## 3. Stabilize first, then find the root cause

### If it's widespread: mitigate before you investigate
| Action | When |
|---|---|
| **Roll back** to the last good version | It started right after a deploy. Fastest and safest. |
| **Turn off a feature flag** | One new feature is crashing things |
| **Fail over / scale up** | The database or a service is overloaded |
| **Put up a status message / workaround** | While the fix is in progress, e.g. "use the website for now" |

> Saying "**restore service first, find the root cause second**" is the point of this whole question. Users care that it works again. You can investigate the cause calmly afterward.

### If it's just him: dig into his specifics
- **Old app version** → ask him to update. (Also check whether we still support that version.)
- **Bad cached data or session on the device** → sign out and back in, or reinstall. *Then* still find out why the app crashed on that data, because it shouldn't.
- **Something unusual about his account data:** a null field, an unusually long name, a permission no one else has. A crash that only hits one user is often **data the code didn't expect**.
  - This is why handling `None` and missing fields matters.
  - **Example:** his profile has no phone number, and the startup screen does `user.phone.format()`.

### Common root causes worth naming
- An **expired certificate, token, or secret** ("it worked yesterday, nothing changed")
- A **vendor API changed** its response shape, and our code wasn't defensive about a missing field
- **Unexpected data**: nulls, empty lists, unusual characters
- The **database ran out of connections**, or a slow query is timing out
- A new **OS version** broke a library
- A **bad config value** deployed separately from code

### Reproduce it
- Use the same app version, OS, and device in a simulator or test device.
- Use a **test account set up like his** (same role and permissions), never his real account or data.
- Once you can reproduce it, write a **failing test** first. Then fix it, and the test proves it stays fixed.

---

## 4. Communicate and prevent

- **Communicate on a schedule**, even if there's no news yet: "still investigating, next update at 3:30."
  - The VP gets a direct reply.
  - For a widespread outage, an incident channel and a status update go to support staff.
- **Blameless postmortem** afterward:
  - A timeline
  - The root cause
  - Why monitoring didn't catch it before a VP did
  - Concrete follow-ups

  "Blameless" means fixing the *system*, not finding someone to blame. That's what makes people report problems honestly.
- **Prevention ideas** to mention:
  - An alarm on the crash rate or 5xx rate, so **we** find out before users call
  - Alerts **30 days before** certificates or secrets expire
  - **Canary releases**, so a bad version reaches 5% of users, not everyone
  - **Defensive code and contract tests** against vendor API responses
  - A **synthetic check**: a script that logs in and opens the app every few minutes, like a robot user

---

## Bonus scenarios they might give instead

### "Loan updates stopped syncing from Encompass since this morning."
1. Check the **SQS queue depth and oldest-message age**. Are events arriving and piling up, or not arriving at all?
2. **Piling up?** The worker is failing. Check the Lambda error logs and the **DLQ**. Likely an Encompass 401 (an **expired OAuth secret**) or a code bug in a new deploy.
3. **Not arriving?** Check the webhook receiver's logs and API Gateway metrics, Encompass's webhook subscription and status page, and whether signature verification is now rejecting everything (did the shared secret rotate?).
4. **Fix it, then replay:** redrive the DLQ, or let the reconciliation poller catch up. Idempotency makes replays safe.

### "The app is slow, not crashed."
1. Is it slow for **everyone**, or just some pages or users?
2. Check **latency metrics by endpoint** (p50 and p95), then **X-Ray traces** to see which hop is slow: our code, the database, or a vendor.
3. If it's the **database**, look for slow queries (`EXPLAIN ANALYZE`), missing indexes, or connection pool exhaustion.
4. If it's a **vendor**, consider timeouts, a cache, and a circuit breaker so their slowness doesn't become ours.

> **p50 / p95 / p99:** the 50th, 95th, and 99th percentile response times. Averages hide pain. If p50 is 200ms but p99 is 8 seconds, 1 in 100 users is having a terrible time.
