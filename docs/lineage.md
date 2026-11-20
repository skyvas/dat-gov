# Lineage

Generated from `src/dat_gov/lineage.py` — do not edit by hand.

```mermaid
flowchart LR
    bronze_departments --> silver_departments
    bronze_courses --> silver_courses
    bronze_faculty --> silver_faculty
    bronze_sections --> silver_sections
    bronze_applicants --> silver_applicants
    bronze_applications --> silver_applications
    bronze_students --> silver_students
    bronze_enrollments --> silver_enrollments
    bronze_tuition_charges --> silver_tuition_charges
    bronze_payments --> silver_payments
    bronze_financial_aid --> silver_financial_aid
    silver_applications --> gold_gold_admissions_funnel
    silver_enrollments --> gold_gold_enrollment
    silver_students --> gold_gold_enrollment
    silver_sections --> gold_gold_enrollment
    silver_courses --> gold_gold_enrollment
    silver_students --> gold_gold_student_retention
    silver_tuition_charges --> gold_gold_finance_summary
    silver_payments --> gold_gold_finance_summary
    silver_financial_aid --> gold_gold_finance_summary
    silver_sections --> gold_gold_faculty_teaching_load
    silver_courses --> gold_gold_faculty_teaching_load
    silver_faculty --> gold_gold_faculty_teaching_load
    silver_enrollments --> gold_gold_faculty_teaching_load

    %% Bronze = raw as received, Silver = cleaned + validated,
    %% Gold = business marts (PII masked).
```

## How to read it

Every Silver dataset has exactly one Bronze parent (its raw file). Every Gold mart lists its Silver sources in `GOLD_SOURCES`; change a Silver dataset and this graph tells you which Gold marts need re-running.
