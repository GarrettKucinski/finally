const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET() {
  const backendResponse = await fetch(`${BACKEND_URL}/api/stream/prices`, {
    headers: { Accept: "text/event-stream" },
  });

  if (!backendResponse.ok || !backendResponse.body) {
    return new Response("Backend SSE unavailable", { status: 502 });
  }

  return new Response(backendResponse.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-store",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
