# Roadmap CLI Demo Project

This is a comprehensive demonstration project showcasing the capabilities of the Roadmap CLI tool. It contains realistic project data that you can use to explore all features without setting up your own project.

## What's Included

- **1,346 Issues** across 5 milestones representing a real software project
- **CloudSync Enterprise Platform** - A realistic project scenario
- **16 Team Members** with proper workload distribution
- **Complete Project Timeline** spanning multiple development phases
- **Rich Issue Data** including priorities, assignees, dependencies, and progress tracking

## Project Structure

```
demo-project/
├── .roadmap/              # Complete roadmap project data
│   ├── config.yaml       # Project configuration
│   ├── issues/           # 1,346 realistic issues
│   └── milestones/       # 5 development milestones
├── demo_scripts/         # Scripts and demonstrations
│   ├── generate_demo_data.py           # Original demo generator
│   ├── generate_large_demo_data.py     # Large-scale demo generator
│   └── demos/            # Feature demonstration scripts
└── README.md             # This file
```

## Quick Start

1. **Navigate to the demo project:**
   ```bash
   cd demo-project
   ```

2. **List all issues:**
   ```bash
   roadmap issue list
   ```

3. **View project analytics:**
   ```bash
   roadmap project
   ```

4. **Export data:**
   ```bash
   roadmap export csv
   roadmap export json --milestone "v1.0 - Foundation"
   ```

5. **Visualize progress:**
   ```bash
   roadmap dashboard
   roadmap burndown
   ```

## Demo Scripts

The `demo_scripts/demos/` directory contains ready-to-run scripts that showcase specific features:

- **`project_analytics_demo.py`** - Project-level insights and team analytics
- **`export_demo.py`** - Data export in multiple formats
- **`visualization_demo.py`** - Interactive charts and dashboards
- **`team_collaboration_demo.py`** - Team management and workload balancing
- **`git_integration_demo.py`** - Git workflow integration
- **`performance_demo.py`** - Performance analysis and optimization
- **`blocked_status_demo.py`** - Issue blocking and dependency management
- **`comment_demo.py`** - Issue commenting and communication
- **`enhanced_list_demo.py`** - Advanced filtering and search

Run any demo script with:
```bash
python demo_scripts/demos/script_name.py
```

## The CloudSync Enterprise Platform

This demo project simulates the development of "CloudSync Enterprise Platform" - a comprehensive cloud synchronization solution. The project includes:

### Milestones
1. **v1.0 - Foundation** - Core infrastructure and basic sync
2. **v1.1 - Enhanced Security** - Advanced security features
3. **v1.2 - Performance** - Optimization and scalability
4. **v1.3 - Advanced Features** - AI and automation capabilities
5. **v2.0 - Enterprise** - Enterprise-grade features

### Teams & Roles
- **Backend Developers** - Core platform development
- **Frontend Developers** - User interface and experience
- **DevOps Engineers** - Infrastructure and deployment
- **Security Engineers** - Security implementation and auditing
- **Product Managers** - Feature planning and coordination
- **QA Engineers** - Testing and quality assurance

### Issue Types
- **Features** - New functionality development
- **Bugs** - Issue fixes and improvements
- **Security** - Security enhancements and audits
- **Performance** - Optimization tasks
- **Documentation** - User and developer documentation

## Key Features Demonstrated

- ✅ **Project Management** - Issue tracking, milestones, and progress monitoring
- ✅ **Team Collaboration** - Assignee management, workload balancing, comments
- ✅ **Analytics** - Project insights, team performance, trend analysis
- ✅ **Data Export** - CSV, JSON, Excel export with filtering
- ✅ **Visualization** - Interactive charts, burndown charts, dashboards
- ✅ **Git Integration** - Branch linking, commit tracking, workflow automation
- ✅ **Performance Analysis** - Bottleneck identification, optimization insights
- ✅ **Filtering & Search** - Advanced issue filtering and search capabilities

## Learning Path

1. **Start with basics**: `roadmap issue list`, `roadmap milestone list`
2. **Explore analytics**: `roadmap project`, `roadmap team`
3. **Try filtering**: `roadmap issue list --status in-progress --assignee alice`
4. **Export data**: `roadmap export csv --milestone "v1.0 - Foundation"`
5. **Visualize**: `roadmap dashboard`, `roadmap burndown`
6. **Run demos**: Execute scripts in `demo_scripts/demos/`

## Regenerating Demo Data

If you want to regenerate or modify the demo data:

```bash
# Generate basic demo (fewer issues)
python demo_scripts/generate_demo_data.py

# Generate large-scale demo (1300+ issues)
python demo_scripts/generate_large_demo_data.py
```

## Notes

- This is **demonstration data only** - not a real project
- All team members and scenarios are fictional
- The project showcases realistic usage patterns and data structures
- Use this project to learn Roadmap CLI features before creating your own

---

**Ready to create your own project?** Navigate back to the parent directory and run `roadmap init` to start fresh!
