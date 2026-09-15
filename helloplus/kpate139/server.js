const http = require("http");
const url = require("url");

const PORT = 3000;

const server = http.createServer((request, response) => {
    const parsedUrl = url.parse(request.url, true);

    response.setHeader("Content-Type", "application/json");

    // Home page
    if (parsedUrl.pathname === "/") {
        response.writeHead(200);

        response.end(JSON.stringify({
            message: "Shopping Assistant API",
            status: "Backend is running!",
            instructions: "Use /search?product=your-product to search."
        }));

        return;
    }

    // Product search
    if (parsedUrl.pathname === "/search") {
        const product = parsedUrl.query.product;

        if (!product) {
            response.writeHead(400);

            response.end(JSON.stringify({
                error: "Please provide a product to search for."
            }));

            return;
        }

        response.writeHead(200);

        response.end(JSON.stringify({
            message: "Shopping Assistant",
            product: product,
            status: "Ready to search for matching products!",
            futureFeature: "The full project will use AI and web APIs to find products."
        }));

        return;
    }

    // Unknown page
    response.writeHead(404);

    response.end(JSON.stringify({
        error: "Page not found."
    }));
});

server.listen(PORT, () => {
    console.log(`Shopping Assistant server running at http://localhost:${PORT}`);
});