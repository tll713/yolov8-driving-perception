const form = document.querySelector("#detectForm");
const resultBox = document.querySelector("#resultBox");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultBox.textContent = "检测中...";

  const formData = new FormData(form);
  const response = await fetch("/api/detect", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  resultBox.textContent = JSON.stringify(data, null, 2);
});
