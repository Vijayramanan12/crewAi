from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from analz_frontend.tools.custom_tool import (
    FetchFrontendSourceTool,
    LibraryFingerprintTool,
    CSSPatternExtractorTool,
)

@CrewBase
class LiveAnalystCrew:
    """
    Experimental Live Analyst Crew for single-URL deep dives.
    """
    agents_config = "config/live_agents.yaml"
    tasks_config = "config/live_tasks.yaml"

    @agent
    def frontend_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_analyst"],
            tools=[
                FetchFrontendSourceTool(),
                LibraryFingerprintTool(),
                CSSPatternExtractorTool(),
            ],
            verbose=True
        )

    @task
    def analyze_live_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_live_task"],
            agent=self.frontend_analyst()
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # Automatically includes all @agent methods
            tasks=self.tasks,    # Automatically includes all @task methods
            process=Process.sequential,
            verbose=True
        )
