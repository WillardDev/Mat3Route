# Mat3Route FastAPI Backend

Production-ready async FastAPI backend exposing the **Mat3Route** Nairobi matatu database with **ThriveWave SMS** credits integration and CORS support for **React** and **Angular** frontends.

---

## 🚀 Live Deployments

- **Production API URL:** `https://mat3route-api.fly.dev`
- **Interactive Swagger Docs:** `https://mat3route-api.fly.dev/docs`
- **ReDoc Documentation:** `https://mat3route-api.fly.dev/redoc`
- **OpenAPI Schema:** `https://mat3route-api.fly.dev/openapi.json`
- **Health Check:** `https://mat3route-api.fly.dev/health`
- **GitHub Repository:** `https://github.com/WillardDev/Mat3Route`

---

## 🛠 Features

1. **PostgreSQL Database Integration**:
   - Async SQLAlchemy 2.0 with asyncpg.
   - Accesses `route_lines`, `saccos`, `routes`, and the `route_info` SQL view.
   - Automated schema migrations and data seeding from `scraped_routes.csv`.

2. **Endpoints for React & Angular Frontends**:
   - `GET /api/v1/routes`: Paginated routes with flexible filtering (start location, end location, matatu line, route number, SACCO, max fare, sorting).
   - `GET /api/v1/routes/{id}`: Single route details.
   - `GET /api/v1/routes/lines`: All 17 matatu lines (A Line, B Line, etc.).
   - `GET /api/v1/routes/saccos`: Transport SACCO operators (Super Metro, NACICO, Double M, 2NK, etc.).
   - `GET /api/v1/routes/search/locations`: Distinct departure and destination stages for search autocomplete dropdowns.
   - `GET /api/v1/routes/stats/summary`: Aggregate analytics (total routes, lines, SACCOs, fare ranges, top destinations).

3. **ThriveWave (ThriveVas) SMS Integration**:
   - `GET /api/v1/sms/credits`: Check available SMS credits/balance on ThriveWave.
   - `POST /api/v1/sms/send`: Send arbitrary SMS alerts and notifications.
   - `POST /api/v1/sms/send-route`: Dispatch route guide and fare details straight to a passenger's phone.
   - `GET /api/v1/sms/pricing`: ThriveWave SMS credit bundle tiers and rates.
   - Built-in simulation / demo fallback when API keys are not yet configured.

4. **Cross-Origin Resource Sharing (CORS)**:
   - Configured to allow `http://localhost:3000` (React Create-React-App), `http://localhost:5173` (React Vite), `http://localhost:4200` (Angular CLI), and production origins via `ALLOWED_ORIGINS`.

---

## 💻 Frontend Consumption Examples

### React (TypeScript / Fetch)

```tsx
// services/routeService.ts
const API_BASE = "https://mat3route-api.fly.dev/api/v1";

export interface RouteInfo {
  id: number;
  line: string;
  route_number: string;
  start: string;
  end: string;
  sacco: string;
  sacco_code: string;
  fare_min: number;
  fare_max: number;
}

export async function fetchRoutes(start?: string, end?: string): Promise<RouteInfo[]> {
  const params = new URLSearchParams();
  if (start) params.append("start", start);
  if (end) params.append("end", end);

  const res = await fetch(`${API_BASE}/routes?${params.toString()}`);
  const data = await res.json();
  return data.items;
}

export async function sendRouteSMS(phone: string, routeId: number) {
  const res = await fetch(`${API_BASE}/sms/send-route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, route_id: routeId }),
  });
  return res.json();
}
```

---

### Angular (HttpClient Service)

```typescript
// src/app/services/mat3route.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RouteResponse {
  total: number;
  skip: number;
  limit: number;
  items: any[];
}

@Injectable({
  providedIn: 'root'
})
export class Mat3RouteService {
  private apiUrl = 'https://mat3route-api.fly.dev/api/v1';

  constructor(private http: HttpClient) {}

  getRoutes(filter?: { start?: string; end?: string; line?: string }): Observable<RouteResponse> {
    let params = new HttpParams();
    if (filter?.start) params = params.set('start', filter.start);
    if (filter?.end) params = params.set('end', filter.end);
    if (filter?.line) params = params.set('line', filter.line);

    return this.http.get<RouteResponse>(`${this.apiUrl}/routes`, { params });
  }

  getSMSCredits(): Observable<any> {
    return this.http.get(`${this.apiUrl}/sms/credits`);
  }

  sendRouteToPhone(phone: string, routeId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/sms/send-route`, {
      phone: phone,
      route_id: routeId
    });
  }
}
```

---

## 🔧 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL asyncpg connection string | `postgresql+asyncpg://...` |
| `THRIVEWAVE_API_KEY` | ThriveWave / ThriveVas SMS API Key | `""` (demo mode) |
| `THRIVEWAVE_API_URL` | ThriveWave API endpoint base URL | `https://api.thrivevas.com/v1` |
| `THRIVEWAVE_SENDER_ID` | SMS Sender ID | `Mat3Route` |
| `ALLOWED_ORIGINS` | Comma-separated list of CORS origins | `*` |
