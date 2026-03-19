from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from datetime import date, datetime

def get_daily_category() -> str:
    categories = {
        "Monday": "Portfolio",
        "Tuesday": "SaaS",
        "Wednesday": "Editorial",
        "Thursday": "E-commerce",
        "Friday": "Experimental",
        "Saturday": "Agency",
        "Sunday": "Wildcard"
    }
    return categories.get(datetime.now().strftime("%A"), "Wildcard")


from analz_frontend.tools.custom_tool import (
    FetchFrontendSourceTool,
    LibraryFingerprintTool,
    CSSPatternExtractorTool,
)


@CrewBase
class FrontendDigestCrew:
    """
    Daily Frontend Digest Crew
    ──────────────────────────
    Agent 1 (WebScout)         → Discovers 5 unique websites per day
    Agent 2 (FrontendAnalyst)  → Deep-reads their full frontend code
    Agent 3 (DocWriter)        → Writes a structured daily Markdown report
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ──────────────────────────────────────────
    # AGENTS
    # ──────────────────────────────────────────

    @agent
    def web_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["web_scout"],
            tools=[
                SerperDevTool(),        # Web search
                ScrapeWebsiteTool(),    # Basic page fetch for validation
            ],
            verbose=True,
            max_iter=10,
        )

    @agent
    def frontend_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_analyst"],
            tools=[
                FetchFrontendSourceTool(),      # Fetch HTML + linked CSS/JS
                LibraryFingerprintTool(),        # Detect frameworks & libraries
                CSSPatternExtractorTool(),       # Extract rare CSS patterns
                ScrapeWebsiteTool(),             # Fallback general scraper
            ],
            verbose=True,
            max_iter=15,
        )

    @agent
    def doc_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["doc_writer"],
            tools=[],   # Pure reasoning + writing — no tools needed
            verbose=True,
        )

    # ──────────────────────────────────────────
    # TASKS
    # ──────────────────────────────────────────

    @task
    def scout_websites_task(self) -> Task:
        today = date.today().strftime("%Y-%m-%d")
        category = get_daily_category()
        return Task(
            config=self.tasks_config["scout_websites_task"],
            agent=self.web_scout(),
            inputs={"today": today, "category": category},
        )

    @task
    def analyze_frontend_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_frontend_task"],
            agent=self.frontend_analyst(),
            context=[self.scout_websites_task()],
        )

    @task
    def write_report_task(self) -> Task:
        today = date.today().strftime("%Y-%m-%d")
        category = get_daily_category()
        return Task(
            config=self.tasks_config["write_report_task"],
            agent=self.doc_writer(),
            context=[self.scout_websites_task(), self.analyze_frontend_task()],
            inputs={"today": today, "category": category},
            output_file=f"knowledge/frontend_digest_{category}_{today}.md",
        )

    # ──────────────────────────────────────────
    # CREW
    # ──────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.web_scout(),
                self.frontend_analyst(),
                self.doc_writer(),
            ],
            tasks=[
                self.scout_websites_task(),
                self.analyze_frontend_task(),
                self.write_report_task(),
            ],
            process=Process.sequential,  # Scout → Analyze → Write, in order
            verbose=True,
        )