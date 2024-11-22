// Handle upload face
document.getElementById("uploadForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("name", document.getElementById("name").value);
    formData.append("file", document.getElementById("file").files[0]);

    const response = await fetch("/add_known_face", {
        method: "POST",
        body: formData,
    });

    const result = await response.json();
    const messageDiv = document.getElementById("uploadMessage");
    if (response.ok) {
        messageDiv.textContent = `${result.message}`;
        messageDiv.classList.add("text-green-500");
    } else {
        messageDiv.textContent = `${result.error}`;
        messageDiv.classList.add("text-red-500");
    }
});

// Handle search face
document.getElementById("searchForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("file", document.getElementById("searchFile").files[0]);

    const response = await fetch("/find_face", {
        method: "POST",
        body: formData,
    });

    const result = await response.json();
    const resultsDiv = document.getElementById("searchResults");
    resultsDiv.innerHTML = "";

    if (response.ok && result.match) {
        result.matches.forEach((match) => {
            const matchDiv = document.createElement("div");
            matchDiv.className = "flex items-center space-x-4 bg-gray-100 p-4 rounded shadow mb-4";
            matchDiv.innerHTML = `
                <img src="static/images_upload/${match.file_name}" alt="${match.name}" class="w-16 h-16 rounded-full">
                <div>
                    <h4 class="text-lg font-bold">${match.name}</h4>
                    <p>Similarity Score: ${match.similarity_score}</p>
                </div>
            `;
            resultsDiv.appendChild(matchDiv);
        });
    } else {
        resultsDiv.textContent = result.message || "No matching faces found.";
        resultsDiv.classList.add("text-gray-600");
    }
});
