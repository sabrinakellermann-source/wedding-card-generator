# Overview

This is a Pinterest-Powered Wedding Invitation Generator that transforms Pinterest board inspiration into AI-generated wedding card designs. The application analyzes images from a user's public Pinterest board, extracts design elements (colors, styles, typography, mood), and generates a personalized A6 landscape wedding invitation design. The tool serves as a prototype for kartenmacherei.de to streamline the wedding invitation design process for couples who have already curated their wedding aesthetic on Pinterest.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Architecture
- **Application Type**: Streamlit web application
- **Design Pattern**: Multi-stage AI pipeline with validation and rendering layers
- **Processing Model**: Concurrent image analysis with retry logic for rate limiting
- **Rationale**: Streamlit provides rapid prototyping capabilities for the PoC phase, while the modular architecture allows for easy iteration and testing of the AI pipeline

## AI Processing Pipeline
- **Core AI Service**: Google Gemini AI via Replit's AI Integrations service
- **Multi-stage Pipeline**:
  1. Image Analysis Stage: Concurrent processing of Pinterest images to extract design elements (colors, styles, mood, typography)
  2. Design Generation Stage: Synthesis of analyzed elements into a structured card design
  3. Validation Stage: Schema validation using Pydantic models
  4. Rendering Stage: Conversion of JSON design to visual output
- **Error Handling**: Tenacity retry logic specifically for rate limiting (429 errors) with exponential backoff (2-128 seconds)
- **Rationale**: The multi-stage approach separates concerns and allows for independent testing/optimization of each pipeline component. The concurrent processing reduces overall generation time to meet the <30 second target

## Data Models & Validation
- **Schema Framework**: Pydantic for type-safe validation
- **Design Constraints**:
  - Fixed A6 landscape format (148mm × 105mm)
  - Standardized element types: text, decorative, image
  - Font restrictions: Serif, Sans-Serif, Script only
  - Font size limits: 12-40pt for readability
  - Predefined decorative patterns: floral-branch, heart-line, geometric-border, leaf-accent, dots-pattern
- **Validation Enforcement**: All AI-generated designs must pass Pydantic validation before rendering
- **Rationale**: Strict schema validation ensures AI outputs are always renderable and align with kartenmacherei.de brand standards, preventing invalid designs from reaching users

## Image Processing & Rendering
- **Rendering Library**: PIL (Pillow) for raster graphics generation
- **Resolution**: 300 DPI for print quality
- **Measurement System**: Millimeters converted to pixels at render time
- **Font Handling**: Fallback to default fonts (with planned enhancement for specific typography)
- **Color System**: Hex color codes validated via regex, converted to RGB for rendering
- **Rationale**: PIL provides sufficient capabilities for the prototype phase, with 300 DPI ensuring professional print quality

## Session Management
- **State Management**: Streamlit session state for design persistence and regeneration tracking
- **Progress Tracking**: Callback-based progress reporting during AI generation
- **User Flow**: URL input → Analysis → Generation → Preview → Regenerate/Edit loop
- **Rationale**: Session state enables "Try Again" functionality and maintains user context across Streamlit reruns

# External Dependencies

## AI Services
- **Google Gemini AI**: Primary AI service for image analysis and design generation
- **Access Method**: Replit AI Integrations service (proxied via custom base URL)
- **Authentication**: API key via environment variable `AI_INTEGRATIONS_GEMINI_API_KEY`
- **Configuration**: Custom base URL via `AI_INTEGRATIONS_GEMINI_BASE_URL`
- **Rate Limiting**: Implements exponential backoff retry logic (7 attempts, 2-128 second delays)

## Pinterest Board Scraping
- **Primary Input Method**: BeautifulSoup-based web scraping (anonymous, no authentication required)
  - Allows access to any public Pinterest board without user login
  - Scrapes image URLs directly from HTML without browser automation
  - Best-effort approach suitable for prototype phase
  - May be unreliable due to Pinterest's bot detection and JavaScript rendering
- **Technical Approach**:
  - HTTP requests with User-Agent headers to mimic browser behavior
  - Multiple extraction strategies: meta tags, img tags, script tags
  - URL normalization to fetch highest quality images (originals/ resolution)
  - Deduplication and validation of Pinterest CDN URLs (pinimg.com)
- **Scraping Heuristics**:
  - Primary: Extract from Open Graph meta tags
  - Secondary: Parse img tags with srcset attributes
  - Fallback: Regex extraction from inline JavaScript
  - Quality optimization: Replace /236x/, /474x/, /564x/ with /originals/
- **Error Handling**:
  - Graceful degradation when scraping fails
  - Clear user messaging about Pinterest bot detection
  - Suggestion to try different boards or manual input fallback
  - Timeout protection (10 seconds per request)
- **Limitations**:
  - Pinterest's JavaScript-heavy pages may limit extraction reliability
  - Bot detection may block requests from Replit IP addresses
  - Success rate varies by board structure and Pinterest's current anti-scraping measures
  - Not suitable for production use (acceptable for prototype/PoC)
- **URL Validation**: Strict allowlist-based validation prevents SSRF attacks while supporting all legitimate Pinterest domains (pinterest.com, pinterest.com.au, de.pinterest.com, etc.)
- **Minimum Image Requirement**: At least 5 pins required for meaningful aesthetic analysis
- **Future Migration Path**: Recommended to use Apify Pinterest scrapers or official Pinterest API for production deployment

## UI Framework
- **Streamlit**: Web application framework for rapid prototyping
- **Layout**: Wide layout mode with multi-column design
- **Page Configuration**: Custom title, icon (💒), and metadata

## Python Libraries
- **Image Processing**: PIL/Pillow
- **HTTP Requests**: requests library for Pinterest scraping
- **HTML Parsing**: BeautifulSoup4
- **Validation**: Pydantic for schema enforcement
- **Concurrency**: concurrent.futures (ThreadPoolExecutor) for parallel image analysis
- **Retry Logic**: tenacity for handling transient failures

## Environment Configuration
- **Environment Variables**:
  - `AI_INTEGRATIONS_GEMINI_API_KEY`: Authentication for Gemini AI
  - `AI_INTEGRATIONS_GEMINI_BASE_URL`: Custom endpoint for Replit's AI proxy
- **Future Considerations**: Database integration not yet implemented (likely Postgres with Drizzle ORM based on typical stack)