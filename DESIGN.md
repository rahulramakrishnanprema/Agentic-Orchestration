# System Design: Aristotle-I Agentic System

**Author(s):** Debabrata Das

## 1. Overview

### 1.1. What is Aristotle-I?

Aristotle-I is an advanced, multi-agent autonomous software engineering system designed to automate the software development lifecycle (SDLC). It integrates with standard development tools like Jira, GitHub, and SonarQube to manage tasks, source code, and code quality. The system leverages multiple Large Language Models (LLMs) to perform complex tasks such as planning, code generation, code review, and documentation.

A core design principle is **Human-in-the-Loop (HITL)** collaboration, allowing human developers to supervise, intervene, and guide the agents at any stage.

### 1.2. Goals

*   **Automate Repetitive Tasks:** Automate the end-to-end process of software development, from task analysis to code implementation and documentation.
*   **Increase Developer Productivity:** Free up human developers to focus on more complex, high-value architectural and design decisions.
*   **Facilitate Human-Agent Collaboration:** Enable a seamless partnership where agents handle the heavy lifting and humans provide oversight, feedback, and final approval.
*   **Improve Code Quality:** Enforce coding standards, security best practices, and completeness through automated, iterative code reviews supervised by humans.
*   **Standardize Documentation:** Automatically generate consistent and comprehensive technical documentation for all completed work.

### 1.3. Non-Goals

*   **Full Autonomy without Oversight:** The system is designed to be a powerful assistant, not a "fire-and-forget" solution. Human oversight is a core feature, not an afterthought.
*   **Infrastructure Management:** This system does not manage or provision cloud infrastructure, CI/CD pipelines, or deployments.
*   **Project Management:** While it integrates with Jira for task management, it is not a project management tool itself.

## 2. System Architecture

The system employs a modular, agent-based architecture where specialized agents collaborate to complete development tasks. This design promotes separation of concerns, scalability, and maintainability, with clear entry points for human intervention.

### 2.1. Architecture Diagram

```mermaid
graph TD
    subgraph "Human Actors"
        User[("User")]
        HumanDeveloper[("Human Developer")]
    end

    subgraph "External Systems & Triggers"
        Jira[("Jira Issue")]
    end

    subgraph "Aristotle-I Agentic Core"
        direction LR
        Planner("Planner Agent")
        Developer("Developer Agent")
        Reviewer("Reviewer Agent")
        Assembler("Assembler Agent")
    end

    subgraph "Supporting Services & Data Stores"
        LLM[/"LLM Service"/]
        MongoDB[("MongoDB")]
        KnowledgeBase[("Knowledge Base (.md files)")]
        SonarQube[("SonarQube")]
        GitHub[("GitHub Repository")]
    end

    subgraph "Outputs"
        FinalCode("Final Code")
        FinalDocs("Final Documentation")
    end

    UI(("React UI"))

    %% Main Workflow
    User -- "Initiates Task" --> Jira
    Jira -- "1. Task Ingestion" --> Planner
    Planner -- "2. Create Plan" --> Developer

    Developer -- "3. Write/Modify Code" --> GitHub
    Developer -- "4. Submit for Review" --> Reviewer

    Reviewer -- "5a. Review Failed (Iterate)" --> Developer
    Reviewer -- "5b. Review Approved" --> Assembler

    Assembler -- "6. Generate Docs" --> FinalDocs
    GitHub -- "7. Push Final Code" --> FinalCode

    %% Human-in-the-Loop Interactions via UI
    HumanDeveloper -- "Reviews Plan" --> Planner
    HumanDeveloper -- "Provides Feedback/Overrides" --> Developer
    HumanDeveloper -- "Reviews & Approves Code" --> Reviewer
    HumanDeveloper -- "Gives Final Approval" --> FinalCode

    %% Agent Dependencies
    Planner -- "Uses" --> LLM
    Developer -- "Uses" --> LLM
    Reviewer -- "Uses" --> LLM
    Assembler -- "Uses" --> LLM

    Reviewer -- "Consults" --> KnowledgeBase
    Reviewer -- "Uses" --> SonarQube
    Reviewer -- "Persists Results" --> MongoDB

    %% UI Interaction
    UI -- "Enables HITL" --> HumanDeveloper
    HumanDeveloper -- "Monitors & Interacts" --> MongoDB

2.2. Component Breakdown
2.2.1. Core Agents
Planner Agent: Ingests a task and breaks it down into a structured plan. The plan is presented in the UI for human review before execution.
Developer Agent: Executes the plan by writing/modifying code. It can receive feedback and corrections from a human developer if it gets stuck or deviates from the intent.
Reviewer Agent: Performs automated code reviews. A human developer can view the review results, override decisions, and provide additional feedback.
Assembler Agent: Generates comprehensive documentation for the completed work.
2.2.2. Supporting Services
LLM Service: Abstraction layer for communicating with various LLM providers.
Database Service (MongoDB): Persists system state, metrics, and review results, making them available for the UI.
UI Service: A React-based web interface that serves as the primary channel for Human-in-the-Loop (HITL) interaction. It allows developers to monitor progress, review artifacts (plans, code), and intervene in the workflow.
2.2.3. External Integrations
Jira: Source of truth for tasks.
GitHub: For all source code management.
SonarQube: For in-depth static analysis.
3. Detailed Design
3.1. Core Workflow with Human-in-the-Loop
Task Ingestion: The workflow is triggered by a new Jira issue.
Planning & Human Review: The Planner Agent generates a step-by-step plan. The system pauses for a human developer to review and approve this plan via the UI.
Development Loop: a. The Developer Agent executes the approved plan, modifying the codebase. b. A human can monitor progress and, if necessary, provide corrective feedback to the agent through the UI.
Review Loop & Human Approval: a. The Reviewer Agent analyzes the code and generates a review report. b. If the automated review fails, the loop iterates with the Developer Agent. A human is alerted if the loop exceeds a set number of attempts (MAX_REBUILD_ATTEMPTS). c. Once the automated review passes, a human developer performs a final check and gives explicit approval via the UI.
Documentation: The Assembler Agent generates the final Markdown document.
Finalization: Upon final human approval, the approved code is committed and pushed to the target branch on GitHub.
3.2. Resilience and Scalability
Resilience:
Human Oversight: The HITL model is the ultimate resilience mechanism, allowing humans to resolve issues that the agents cannot handle autonomously.
Robust Parsing: Uses json_repair to handle malformed LLM responses.
Configuration-Driven: All settings are managed via .env for quick reconfiguration.
Scalability:
Parallelism: The Reviewer Agent processes files in parallel.
Stateless Agents: The architecture allows for running multiple agent workflows in parallel, with human developers able to supervise multiple tasks simultaneously through the UI.
4. Security Considerations
Credential Management: Secrets in .env must be strictly controlled. For production, use a secrets management service (e.g., HashiCorp Vault).
Permissions: The GitHub PAT should be scoped with the minimum required permissions (repo).
Prompt Injection: Inputs from external sources (Jira tickets) must be sanitized. Human review of the initial plan provides a safeguard against malicious instructions.
Code Security: The combination of SonarQube, the Reviewer Agent, and final human approval is critical for catching vulnerabilities in LLM-generated code.
5. Monitoring and Observability
Data Persistence: All significant events and agent outputs are persisted to MongoDB for audit and review.
Monitoring & Intervention UI: The React UI is the central hub for both monitoring and intervention. It provides visibility into:
Ongoing agent tasks and their current status (e.g., "Pending Human Review").
Historical performance metrics and review scores.
An interface for providing feedback, corrections, and approvals.
Key Metrics to Track:
Task success/failure rate.
End-to-end task completion time (including human review time).
Number of automated review cycles per task.
Instances of human intervention/overrides.
6. Alternatives Considered
Fully Autonomous System: A model without built-in HITL checkpoints was considered but rejected. The risk of undesirable or incorrect autonomous actions was deemed too high. A collaborative approach provides a safer and more practical path to automation.
Monolithic Agent: A single agent was rejected in favor of a multi-agent system, which is easier to debug, maintain, and provides clearer points for human intervention.
