---
id: "94ed94c5"
name: "Test Project"
description: "Testing priority and status fixes"
status: "planning"
priority: "critical"
owner: "testuser"
start_date: ""
target_end_date: ""
actual_end_date: null
created: "2025-10-11T19:16:33.481290"
updated: "2025-10-11T19:16:33.481290"
milestones:
  - "milestone_1"
  - "milestone_2"
estimated_hours: 4.0
actual_hours: null
---

# Test Project

## Project Overview

Testing priority and status fixes

**Project Owner:** testuser
**Status:** planning
**Timeline:**  →

## Objectives

- [ ] Objective 1
- [ ] Objective 2
- [ ] Objective 3

## Milestones & Timeline

{% for milestone in milestones %}
- **{{ milestone }}** - [Link to milestone](../milestones/{{ milestone }}.md)
{% endfor %}

## Timeline Tracking

- **Start Date:** 
- **Target End Date:** 
- **Actual End Date:** {{ actual_end_date }}
- **Estimated Hours:** 4.0
- **Actual Hours:** {{ actual_hours }}

## Notes

Project notes and additional context.

---
*Last updated: 2025-10-11T19:16:33.481290*