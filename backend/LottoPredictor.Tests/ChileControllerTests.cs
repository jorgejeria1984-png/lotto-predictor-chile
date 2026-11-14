using System.Net;
using System.Net.Http;
using System.Text;
using LottoPredictor.Api.Controllers;
using Microsoft.AspNetCore.Mvc;

namespace LottoPredictor.Tests;

public class ChileControllerTests
{
    private sealed class FakeHandler(HttpStatusCode code, string body) : HttpMessageHandler
    {
        public string? Path { get; private set; }
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Path = request.RequestUri?.PathAndQuery;
            return Task.FromResult(new HttpResponseMessage(code)
            {
                Content = new StringContent(body, Encoding.UTF8, "application/json")
            });
        }
    }

    private sealed class Factory(FakeHandler handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) =>
            new HttpClient(handler, disposeHandler: false) { BaseAddress = new Uri("http://127.0.0.1:8765/") };
    }

    [Fact]
    public async Task RejectsUnknownGame()
    {
        var handler = new FakeHandler(HttpStatusCode.OK, "{}");
        var result = await new ChileController(new Factory(handler)).Analysis("other");
        Assert.IsType<BadRequestObjectResult>(result);
        Assert.Null(handler.Path);
    }

    [Theory]
    [InlineData("loto", 200)]
    [InlineData("kino", 400)]
    public async Task ForwardsJsonAndStatus(string game, int status)
    {
        var handler = new FakeHandler((HttpStatusCode)status, "{\"ok\":true}");
        var result = Assert.IsType<ContentResult>(await new ChileController(new Factory(handler)).Analysis(game));
        Assert.Equal(status, result.StatusCode);
        Assert.Equal("{\"ok\":true}", result.Content);
        Assert.Equal("/chile-api/analysis?game=" + game, handler.Path);
    }
}
