---
id: "{{ project_id }}"
name: "{{ project_name }}"
description: "{{ project_description }}"
status: "planning"
priority: "medium"
owner: "{{ project_owner }}"
start_date: "{{ start_date }}"
target_end_date: "{{ target_end_date }}"
actual_end_date: null
created: "{{ created_date }}"
updated: "{{ updated_date }}"
milestones:
  - "{{ milestone_1 }}"
  - "{{ milestone_2 }}"
estimated_hours: {{ estimated_hours }}
actual_hours: null
---

# {{ project_name }}

## Project Overview

{{ project_description }}

**Project Owner:** {{ project_owner }}
**Status:** {{ status }}
**Timeline:** {{ start_date }} → {{ target_end_date }}

## Objectives

- [ ] Objective 1
- [ ] Objective 2
- [ ] Objective 3

## Milestones & Timeline

{% for milestone in milestones %}
- **{{ milestone }}** - [Link to milestone](../milestones/{{ milestone }}.md)
{% endfor %}

## Timeline Tracking

- **Start Date:** {{ start_date }}
- **Target End Date:** {{ target_end_date }}
- **Actual End Date:** {{ actual_end_date }}
- **Estimated Hours:** {{ estimated_hours }}
- **Actual Hours:** {{ actual_hours }}

## Notes

Project notes and additional context.

---
*Last updated: {{ updated_date }}*
