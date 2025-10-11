# Data Visualization Features 📊

The Roadmap CLI now includes comprehensive data visualization capabilities for generating charts and graphs from issue/milestone data, perfect for stakeholder reporting and project analysis.

## Overview

The visualization system provides:

- **Multiple Chart Types**: Status distribution, burndown charts, velocity trends, milestone progress, team workload
- **Interactive & Static Output**: HTML (Plotly), PNG, SVG formats
- **Professional Dashboards**: Executive-ready stakeholder reports
- **Flexible Filtering**: By milestone, assignee, time periods
- **Integration**: Built on existing pandas analytics foundation

## Quick Start

### Generate Status Distribution Chart

```bash
# Interactive donut chart
roadmap visualize status --chart-type donut --format html

# Bar chart for specific milestone  
roadmap visualize status --chart-type bar --milestone "v1.0"

# PNG chart for specific assignee
roadmap visualize status --assignee john --format png
```

### Generate Burndown Chart

```bash
# Burndown for all issues
roadmap visualize burndown

# Burndown for specific milestone
roadmap visualize burndown --milestone "Sprint 1"

# Static PNG format
roadmap visualize burndown --format png
```

### Generate Team Velocity Chart

```bash
# Weekly velocity trends (default)
roadmap visualize velocity

# Monthly analysis
roadmap visualize velocity --period M

# Daily velocity tracking
roadmap visualize velocity --period D --format svg
```

### Generate Milestone Progress

```bash
# Overview of all milestones
roadmap visualize milestones

# Static PNG format
roadmap visualize milestones --format png
```

### Generate Team Workload Analysis

```bash
# Team workload distribution
roadmap visualize team

# SVG format for presentations
roadmap visualize team --format svg
```

### Generate Stakeholder Dashboard

```bash
# Comprehensive interactive dashboard
roadmap visualize dashboard

# Dashboard for specific milestone
roadmap visualize dashboard --milestone "v1.0"

# Custom output location
roadmap visualize dashboard --output quarterly_report.html
```

## Chart Types

### 1. Status Distribution Charts

**Purpose**: Show distribution of issues across statuses (todo, in-progress, blocked, review, done)

**Chart Types**:
- `pie`: Traditional pie chart
- `donut`: Donut chart with center hole
- `bar`: Horizontal or vertical bar chart

**Use Cases**:
- Project health assessment
- Bottleneck identification
- Sprint/milestone progress overview

### 2. Burndown Charts

**Purpose**: Track work remaining over time vs ideal completion rate

**Features**:
- Ideal burndown line (linear)
- Actual burndown line
- Milestone-specific analysis

**Use Cases**:
- Sprint progress tracking
- Velocity analysis
- Timeline adherence monitoring

### 3. Velocity Charts

**Purpose**: Show team productivity trends over time

**Metrics**:
- Issues completed per period
- Velocity score calculation
- Trend analysis

**Periods**:
- `D`: Daily analysis
- `W`: Weekly analysis (default)
- `M`: Monthly analysis

### 4. Milestone Progress Charts

**Purpose**: Overview of progress across all milestones

**Features**:
- Completion percentages
- Issue counts (completed/total)
- Color-coded progress levels
- Due date ordering

### 5. Team Workload Charts

**Purpose**: Analyze workload distribution across team members

**Metrics**:
- Total issues per assignee
- Estimated hours per assignee
- Workload balance analysis

### 6. Stakeholder Dashboard

**Purpose**: Comprehensive executive-ready report combining all visualizations

**Includes**:
- Summary metrics cards
- Status distribution (donut chart)
- Milestone progress overview
- Team velocity trends
- Team workload analysis
- Professional styling and branding

## Output Formats

### HTML (Interactive)
- **Technology**: Plotly.js
- **Features**: Interactive tooltips, zoom, pan
- **Best For**: Online viewing, presentations, stakeholder sharing
- **File Size**: Larger (includes JavaScript)

### PNG (Static Images)
- **Technology**: Matplotlib
- **Features**: High-resolution, print-ready
- **Best For**: Reports, documentation, presentations
- **File Size**: Medium

### SVG (Vector Graphics)
- **Technology**: Matplotlib
- **Features**: Scalable, editable
- **Best For**: Print materials, design flexibility
- **File Size**: Small

## File Organization

All generated visualizations are stored in the artifacts directory:

```
.roadmap/artifacts/
├── charts/                          # Individual charts
│   ├── status_distribution_*.html
│   ├── burndown_chart_*.png
│   ├── velocity_chart_*.svg
│   ├── milestone_progress_*.html
│   └── team_workload_*.png
└── dashboards/                      # Comprehensive dashboards
    └── stakeholder_dashboard_*.html
```

## Advanced Usage

### Filtering Options

```bash
# Status chart for specific milestone
roadmap visualize status --milestone "v2.0" --chart-type bar

# Team workload for completed issues only
roadmap visualize team --status done

# Burndown for specific assignee's issues
roadmap visualize burndown --assignee "john-doe"
```

### Custom Output Paths

```bash
# Save to specific location
roadmap visualize dashboard --output /path/to/report.html

# Save with custom naming
roadmap visualize status --output weekly_status_$(date +%Y%m%d).png
```

### Automated Reporting

```bash
#!/bin/bash
# Generate weekly stakeholder report
DATE=$(date +%Y%m%d)
roadmap visualize dashboard --output "weekly_report_$DATE.html"
echo "Report generated: weekly_report_$DATE.html"
```

## Integration with Analytics

The visualization system builds on the existing analytics foundation:

- **Data Source**: Uses pandas DataFrames from `DataFrameAdapter`
- **Analytics Engine**: Leverages `DataAnalyzer` for metrics calculation
- **Enhanced Analytics**: Compatible with `EnhancedAnalyzer` insights
- **Export Integration**: Complements CSV/Excel export capabilities

## Use Cases

### Project Managers
- **Weekly Status Reviews**: Generate status distribution charts
- **Sprint Planning**: Use burndown and velocity charts
- **Stakeholder Updates**: Create comprehensive dashboards

### Team Leads
- **Team Performance**: Analyze workload distribution
- **Capacity Planning**: Track velocity trends
- **Bottleneck Identification**: Monitor blocked/in-progress ratios

### Executives/Stakeholders  
- **Executive Dashboards**: Comprehensive project overview
- **Milestone Tracking**: Visual progress reports
- **Performance Metrics**: Team productivity insights

### DevOps/Process
- **CI/CD Integration**: Automated report generation
- **Trend Analysis**: Long-term velocity and quality metrics
- **Data-Driven Decisions**: Visual insights for process improvements

## Technical Architecture

### Backend Libraries
- **Matplotlib**: Static chart generation (PNG, SVG)
- **Plotly**: Interactive chart generation (HTML)
- **Seaborn**: Enhanced styling and color palettes
- **Pandas**: Data manipulation and analysis

### Chart Generator Classes
- `ChartGenerator`: Core chart generation functionality
- `DashboardGenerator`: Comprehensive dashboard creation
- `VisualizationError`: Custom exception handling

### Security & Performance
- **Secure File Operations**: All outputs use secure file creation
- **Memory Management**: Efficient handling of large datasets
- **Error Handling**: Graceful failure with informative messages
- **File Validation**: Path sanitization and security checks

## Troubleshooting

### Common Issues

**No data available**:
```bash
# Check if issues exist
roadmap issue list

# Initialize roadmap if needed
roadmap init
```

**Permission errors**:
```bash
# Check artifacts directory permissions
ls -la .roadmap/artifacts/

# Ensure write access
chmod 755 .roadmap/artifacts/
```

**Missing dependencies**:
```bash
# Reinstall visualization dependencies
poetry install
```

### Performance Optimization

For large datasets (>1000 issues):
- Use filtering options to reduce dataset size
- Generate PNG/SVG instead of HTML for better performance
- Consider time-based filtering for historical analysis

## Examples Gallery

### Status Health Check
```bash
roadmap visualize status --chart-type donut --format html
```
Perfect for daily standups and sprint reviews.

### Sprint Burndown
```bash
roadmap visualize burndown --milestone "Sprint 3" --format png
```
Track sprint progress against planned timeline.

### Team Performance Review
```bash
roadmap visualize team --format html
```
Identify workload imbalances and capacity issues.

### Executive Summary
```bash
roadmap visualize dashboard --output executive_summary.html
```
Comprehensive overview for stakeholder presentations.

---

**Next Steps**: The visualization system provides a solid foundation for data-driven project management. Future enhancements could include custom chart configurations, additional chart types, and real-time dashboard updates.