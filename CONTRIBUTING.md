# Contributing

Thank you for helping build the Spec-Driven Development course.

## Before opening a change

1. Read the [course plan](COURSE_PLAN.md) and [curriculum map](curriculum/README.md).
2. Keep each lesson in `curriculum/<level>/<number-topic>/` with one `README.md`, one primary notebook, and one reusable `lab.py`.
3. Make default labs deterministic, credential-free, and safe to run locally.
4. Cite primary specifications or official documentation close to technical claims.
5. Update `hub/lessons.js`, the quiz, and curriculum navigation when publishing a lesson.
6. For intermediate and advanced lessons, modify or evaluate a realistic software artifact in addition to any isolated simulation; connect repository work to explicit evidence and failure analysis.

Run the complete local check before submitting:

```bash
python3 scripts/validate_course.py
python3 -m unittest discover -s tests -v
```

Do not add placeholder lesson folders merely to make the roadmap look complete. A planned topic belongs in `COURSE_PLAN.md` until its complete vertical slice is ready.
