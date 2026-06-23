# API Documentation

This document outlines the REST APIs available in the `q4s_site_monitoring` project.

## Base URL
All application API endpoints are prefixed with `/api/`.

---

## 1. OPC Generated Site Links API

This API provides standard CRUD operations for the `OPCGeneratedSiteLink` model.

**Endpoint:** `/api/opc-generated-site-links/`

### Authentication & Permissions
- **Authentication:** Basic Authentication
- **Permissions:** Requires authenticated user (`IsAuthenticated`)

### Available Methods

- `GET /api/opc-generated-site-links/` - List all site links.
- `POST /api/opc-generated-site-links/` - Create a new site link.
- `GET /api/opc-generated-site-links/{id}/` - Retrieve a specific site link by ID.
- `PUT /api/opc-generated-site-links/{id}/` - Update a specific site link.
- `PATCH /api/opc-generated-site-links/{id}/` - Partially update a specific site link.
- `DELETE /api/opc-generated-site-links/{id}/` - Delete a specific site link.

### Model Fields

**Read/Write Fields:**
- `id` (String, Max Length: 64, Primary Key) - UUID or similar unique identifier.
- `site` (Integer, Optional)
- `url` (String)
- `username` (String, Max Length: 64, Optional, Default: "")
- `last_synced_at` (DateTime, Optional)
- `is_active` (Boolean, Default: True)
- `is_deleted` (Boolean, Default: False)
- `expire_date` (DateTime)
- `filter_start_date` (DateTime)
- `filter_end_date` (DateTime)

**Write-Only Fields:**
- `password_hash` (String, Max Length: 128) - Hash of the password, never returned in responses.
- `json_data` (JSON, Optional) - The payload data, never returned in responses from this endpoint.

**Read-Only Fields:**
- `created_at` (DateTime) - Automatically set on creation.

---

## 2. Site Dashboard Access API

This API validates access to a site dashboard link using a password and returns the site link details and associated JSON data.

**Endpoint:** `/api/site-dashboard/{link_id}/access/`
**Method:** `POST`

### Authentication & Permissions
- **Authentication:** No global authentication required.
- **Ratelimiting:** This endpoint is rate-limited.
- **Authorization Header:** Requires the password provided as a Bearer token.
  - Format: `Authorization: Bearer <password>`

### Path Parameters
- `link_id` (String) - The ID of the `OPCGeneratedSiteLink`.

### Responses

#### Success (200 OK)
Returned when the link exists, is active, not deleted, not expired, and the provided password matches the stored hash.

```json
{
  "ok": true,
  "id": "<link_id>",
  "site": 123,
  "username": "user1",
  "expire_date": "2026-12-31T23:59:59Z",
  "filter": {
      "from": "2026-01-01T00:00:00Z",
      "to": "2026-12-31T23:59:59Z"
  },
  "data": { ... } // Contains the stored json_data
}
```

#### Error (404 Not Found)
Returned when the link ID does not exist, is marked as deleted, or is not active.

```json
{
  "ok": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Link not found."
  }
}
```

#### Error (410 Gone)
Returned when the link exists but the `expire_date` has passed.

```json
{
  "ok": false,
  "error": {
    "code": "EXPIRED",
    "message": "Link expired."
  }
}
```

#### Error (401 Unauthorized)
Returned when the Authorization header is missing, incorrectly formatted, or the password does not match the stored hash.

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid password."
  }
}
```
