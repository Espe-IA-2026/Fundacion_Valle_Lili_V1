from pathlib import Path

import httpx

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.extractors import HttpClient, RobotsFetchResult, RobotsPolicy, WebCrawler
from semantic_layer_fvl.orchestrator.pipeline import SemanticPipeline


def test_pipeline_process_url_end_to_end(workspace_tmp_path: Path) -> None:
    html = """
    <html>
      <head><title>Servicio de Cardiologia</title></head>
      <body>
        <nav>Menu</nav>
        <main>
          <p>Atencion cardiovascular integral.</p>
          <p>Equipo especializado.</p>
        </main>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(url=robots_url, status_code=200, text="User-agent: *\nAllow: /\n")

    settings = Settings(output_dir=workspace_tmp_path, requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )
    pipeline = SemanticPipeline(settings=settings, crawler=crawler)

    processed, output_path = pipeline.process_url(
        "https://valledellili.org/servicios/cardiologia",
        write=False,
    )
    client.close()

    assert processed.document.slug == "cardiologia"
    assert output_path is None
    assert "Equipo especializado." in processed.content_markdown
