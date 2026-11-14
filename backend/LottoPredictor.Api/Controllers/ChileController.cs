using Microsoft.AspNetCore.Mvc;

namespace LottoPredictor.Api.Controllers;

/// <summary>Read-only gateway to the local Chile analysis service; original lottery storage is unchanged.</summary>
[ApiController]
public sealed class ChileController(IHttpClientFactory clients) : ControllerBase
{
    [HttpGet("api/chile/analysis")]
    public async Task<IActionResult> Analysis([FromQuery] string game = "loto", CancellationToken ct = default)
    {
        if (game is not ("loto" or "kino"))
            return BadRequest(new { error = "Juego inválido." });

        try
        {
            using var client = clients.CreateClient("ChileAnalysis");
            using var response = await client.GetAsync("chile-api/analysis?game=" + game, ct);
            var payload = await response.Content.ReadAsStringAsync(ct);
            if (response.Content.Headers.ContentType?.MediaType != "application/json")
                return StatusCode(502, new { error = "Respuesta no válida del servicio Chile." });
            return new ContentResult
            {
                Content = payload,
                ContentType = "application/json; charset=utf-8",
                StatusCode = (int)response.StatusCode
            };
        }
        catch (HttpRequestException)
        {
            return StatusCode(503, new { error = "Inicie el servicio local con py chile/app.py." });
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            return StatusCode(504, new { error = "El análisis no terminó dentro del tiempo de solicitud." });
        }
    }
}
