# Roomy Assistant — TODO

## Planned Features (Not Yet Implemented)

### Content & Resources
- [ ] Add installation video cards (YouTube/Brightcove embeds) — link to F&D workshop videos
- [ ] Add workshop cards — free in-store tile installation workshops (first Saturday of every month)
- [ ] Add care guide cards — tile cleaning & maintenance guides, PDFs, blog articles
- [ ] Wire up the knowledge_base.py resource definitions from the architecture guide

### Search & Data
- [ ] Add more flooring categories: wood, vinyl, laminate, stone, decoratives
- [ ] Add pagination support (currently max 10 results per search)
- [ ] Add real-time inventory/stock data
- [ ] Integrate Algolia search (needs search-only API key from F&D platform team)
- [ ] Integrate SFCC OCAPI for full product catalog (needs client_id)
- [ ] Improve color/finish extraction accuracy beyond heuristic regex
- [ ] Add size fuzzy matching (e.g. "one foot square" → "12 x 12")

### Agent Capabilities
- [ ] Add product comparison feature
- [ ] Add follow-up question suggestions after search results
- [ ] Add conversation memory across sessions (persistent checkpointer)
- [ ] Support multi-language queries

### UI/UX
- [ ] Add product detail expansion (click card for full description)
- [ ] Add wishlist/favorites functionality
- [ ] Add "Ask Roomy" embed script for F&D site (roomy-widget.js)
- [ ] Style the sidebar to match F&D brand colors (green header, red CTAs)

### Deployment
- [ ] Dockerize the Python backend for ECS Fargate
- [ ] Deploy frontend to AWS Amplify
- [ ] Configure SFCC CSP headers for embed
- [ ] Add CORS for production F&D domain
