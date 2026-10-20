async function request(path, options) {
  let response;

  try {
    response = await fetch(path, options);
  } catch {
    throw new Error(
      "Cannot reach the backend. Make sure the API is running on port 8000."
    );
  }

  if (!response.ok) {
    let detail = "";

    try {
      detail = (await response.json()).detail;
    } catch {
      // ignore body parse errors
    }

    throw new Error(detail || `Request failed (${response.status})`);
  }

  return response.json();
}

export const getHealth = () => request("/api/health");

export const getBenchmarkQuestions = () =>
  request("/api/benchmark-questions");

export const startValidation = (question, category) =>
  request("/api/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, category }),
  });

export const getRun = (id) => request(`/api/runs/${id}`);

export const getHistory = () => request("/api/history");
