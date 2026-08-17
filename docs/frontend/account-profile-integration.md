# Customer Profile & Gallery — Frontend Integration Guide

Audience: frontend engineers integrating the customer profile modules into the Next.js app.

---

## 1. Ground rules

| Rule | Detail |
| --- | --- |
| Base path | `/v1` |
| Method | **`POST` for every endpoint.** A middleware rejects `GET`/`PUT`/`PATCH`/`DELETE` with HTTP 400. Endpoints that only read still use `POST` with an empty body `{}`. |
| Content type | `application/json` |
| Casing | **camelCase** in both requests and responses. |
| Auth | `Authorization: Bearer <accessToken>` on every profile/gallery call. |
| Account scoping | The account is derived from the token. Never send your own `accountId` — the only exception is `albums/list-public`, where it identifies *someone else's* account. |

### Response envelope

Success:

```json
{ "status": "ok", "output": { /* endpoint payload, may be null */ } }
```

Business error (HTTP 200):

```json
{ "status": "error", "errorMessage": "human readable reason" }
```

Validation / not-found / conflict errors are raised as real HTTP status codes with FastAPI's
default body — **a different shape**:

```json
{ "detail": "traveller not found" }
```

| Status | Meaning |
| --- | --- |
| 200 | Success, or a business error envelope |
| 401 | Missing/expired token, or account not `ACTIVE` |
| 404 | Album, image or traveller not found (or not owned by you) |
| 409 | Tried to rename or delete a system album |
| 422 | Unknown key in the body, or an invalid field (bad UUID, bad birth month, unsupported image type, oversized image) |

Handle both shapes:

```ts
type ApiEnvelope<T> =
  | { status: 'ok'; output: T }
  | { status: 'error'; errorMessage: string };

export async function apiPost<T>(path: string, body: unknown, token: string): Promise<T> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body ?? {}),
  });

  const json = await res.json();

  if (!res.ok) {
    // 401/404/409/422 -> { detail: string }
    throw new ApiError(json?.detail ?? 'Request failed', res.status);
  }
  if (json.status === 'error') {
    throw new ApiError(json.errorMessage, 200);
  }
  return json.output as T;
}
```

---

## 2. Partial update semantics — read this before building forms

Every update endpoint is a **partial update**, driven by which keys are present in the JSON body:

| You send | Result |
| --- | --- |
| key omitted entirely | field left unchanged |
| `"nationality": "Indian"` | field set |
| `"nationality": null` | field **cleared** |
| an unrecognised key | **HTTP 422** — the whole request is rejected |

Unknown keys are rejected rather than ignored, so a misspelled field fails loudly instead of
returning 200 with nothing changed. The error names the offending key:

```json
{ "detail": [{ "type": "extra_forbidden", "loc": ["body", "flightPref"], "msg": "Extra inputs are not permitted" }] }
```

Note that for 422 responses `detail` is an **array** of Pydantic errors, not a string.

This means **you must not send a whole form snapshot**. Sending every field on every save is
harmless for values the user edited, but it makes "clear this field" indistinguishable from
"I didn't touch it" only if you send `null` for empty inputs — which would wipe data the user
never looked at.

Build a dirty-fields payload:

```ts
// react-hook-form gives you dirtyFields; only send what changed.
const payload = Object.fromEntries(
  Object.keys(formState.dirtyFields).map((k) => [k, values[k] === '' ? null : values[k]])
);
await apiPost('/account/profile/personal', payload, token);
```

`JSON.stringify` drops `undefined` values, so setting a field to `undefined` is a clean way to
omit it. Setting it to `null` explicitly clears it server-side.

**Nested objects (`location`, `emergencyContact`, `alternativePhone`) are replaced wholesale,
not merged.** To change only the city you must resend the full `location` object. To remove
one, send `null`.

**List fields are full replacements.** `destinations` and each of its five arrays overwrite
what is stored. To add one country, send the complete new array.

---

## 3. Types

```ts
export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say';
export type PreferredContactMethod = 'email' | 'phone';
export type FlightClass = 'economy' | 'premium_economy' | 'business' | 'first';
export type FlightPriority = 'best_value' | 'direct_flight' | 'flexible_tickets' | 'better_timings';
export type TripPace = 'relaxed' | 'balanced' | 'fast_paced';
export type BaggageStyle = 'light_packer' | 'checked_baggage_okay';
export type AlbumVisibility = 'public' | 'private';
export type AlbumKind = 'user' | 'default' | 'profile';
export type ImageStatus = 'pending' | 'ready';

// Tier is a display string assigned by the rewards system. Note the accented values.
export type CustomerTier = 'Novus' | 'Aurea' | 'Privé' | 'Elite' | 'Échelon';

export interface CityLocation {
  cityName: string;
  countryCode: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface PersonalInfo {
  firstName: string | null;
  lastName: string | null;
  gender: Gender | null;
  dateOfBirth: string | null;   // "YYYY-MM-DD"
  nationality: string | null;
  location: CityLocation | null;
  language: string;             // default "en"
  description: string;          // default ""
  email: string | null;
  dialCode: string;             // read-only
  phoneNumber: string;          // read-only
  facebook: string | null;
  instagram: string | null;
  linkedin: string | null;
}

export interface ContactInfo {
  email: string | null;
  dialCode: string;             // read-only
  phoneNumber: string;          // read-only
  alternativeDialCode: string | null;
  alternativePhoneNumber: string | null;
  preferredContactMethod: PreferredContactMethod;
  emergencyContact: { firstName: string; dialCode: string; phoneNumber: string } | null;
}

export interface TravelPreferences {
  stayHotels: boolean;
  stayVillas: boolean;
  stayResorts: boolean;
  stayBoutiqueHotels: boolean;
  stayCruises: boolean;
  flightClass: FlightClass;
  flightPriority: FlightPriority;
  tripPace: TripPace;
  baggageStyle: BaggageStyle;
}

export interface PreferredDestinations {
  countriesVisited: string[];
  indianStatesVisited: string[];
  placesLoved: string[];
  placesRecommended: string[];
  travelMomentsEnjoyed: string[];
}

export interface FrequentTraveller {
  travellerId: string;
  firstName: string;
  lastName: string | null;
  relationship: string | null;
  nationality: string | null;
  gender: Gender | null;
  birthYear: number | null;     // month + year only, no day
  birthMonth: number | null;    // 1-12
  passportMasked: string | null; // "******1234" — plaintext is never returned
}

export interface AccountProfile {
  personal: PersonalInfo;
  contact: ContactInfo;
  preferences: TravelPreferences;
  destinations: PreferredDestinations;
  travellers: FrequentTraveller[];
  tier: CustomerTier;           // read-only
  badges: string[];             // read-only
  profilePictureUrl: string | null; // presigned, expires — see §6
  completionPercentage: number; // 0-100
}
```

### Read-only fields

`dialCode`, `phoneNumber`, `tier`, `badges`, `completionPercentage` and `profilePictureUrl`
appear in responses only. They are rejected if sent in a request body.

- **Phone number is the login identity and cannot be changed here.** Render it disabled.
- **Email is editable** via the personal section and is stored **unverified** — there is no
  confirmation email today. Don't imply verification in the UI.
- `tier` and `badges` are awarded by the rewards system. Display only.

### Defaults

A profile row is created lazily on first read, so `profile/get` never 404s for a valid account.
Initial values: `language: "en"`, `description: ""`, `preferredContactMethod: "phone"`, all
stay toggles `false`, `flightClass: "economy"`, `flightPriority: "best_value"`,
`tripPace: "balanced"`, `baggageStyle: "light_packer"`, `tier: "Novus"`, `badges: []`.

### completionPercentage

Computed from eleven optional fields: first name, last name, gender, date of birth,
nationality, location, description, any social link, alternative phone, emergency contact,
profile picture. Useful for a "complete your profile" nudge.

---

## 4. Profile endpoints

All paths are relative to `/v1`.

| Path | Body | `output` |
| --- | --- | --- |
| `/account/profile/get` | `{}` | `AccountProfile` |
| `/account/profile/personal` | partial personal fields | `AccountProfile` |
| `/account/profile/contact` | partial contact fields | `AccountProfile` |
| `/account/profile/preferences` | partial preference fields | `AccountProfile` |
| `/account/profile/destinations` | any of the five arrays | `AccountProfile` |
| `/account/profile/travellers/list` | `{}` | `{ travellers: FrequentTraveller[] }` |
| `/account/profile/travellers/add` | traveller fields | `FrequentTraveller` |
| `/account/profile/travellers/update` | `{ travellerId, ...partial }` | `FrequentTraveller` |
| `/account/profile/travellers/remove` | `{ travellerId }` | `null` |
| `/account/profile/picture/set` | `{ imageId }` | `{ profilePictureImageId }` |
| `/account/profile/picture/clear` | `{}` | `{ profilePictureImageId: null }` |

**Every section update returns the full `AccountProfile`.** Use the response to replace your
cached profile — no refetch needed, and `completionPercentage` stays in sync.

### Examples

```jsonc
// POST /v1/account/profile/personal — set names and location, clear nationality
{
  "firstName": "Asha",
  "lastName": "Menon",
  "nationality": null,
  "location": { "cityName": "Goa", "countryCode": "IN", "latitude": 15.29, "longitude": 74.12 }
}
```

```jsonc
// POST /v1/account/profile/contact — remove the emergency contact, keep everything else
{ "emergencyContact": null }
```

```jsonc
// POST /v1/account/profile/preferences — toggle two stays, leave the rest alone
{ "stayVillas": true, "stayCruises": true }
```

```jsonc
// POST /v1/account/profile/travellers/add
{
  "firstName": "Ravi", "lastName": "Menon", "relationship": "spouse",
  "nationality": "Indian", "gender": "male",
  "birthYear": 1988, "birthMonth": 4,
  "passportNumber": "Z1234567"
}
```

**Traveller date of birth is month + year only.** Send `birthYear` and `birthMonth` together or
neither — sending one alone returns 422. A future month is rejected.

**Passport numbers are write-only.** You send `passportNumber` in plaintext (over TLS); reads
return `passportMasked` only. There is no way to read the full number back, so an "edit
passport" field must start empty and only be submitted when the user retypes it.

---

## 5. Gallery model

- Images live in a **private** S3 bucket. The API never receives image bytes.
- An image belongs to **exactly one** album.
- Two **system albums** are auto-created on first gallery access:
  - `My Photos` (`kind: "default"`) — where uploads land when no `albumId` is given.
  - `Profile` (`kind: "profile"`) — the only album whose images can become the profile picture.
- System albums **cannot be renamed, re-described, made public, or deleted** → HTTP 409.
  You may still set their cover image. Hide the rename/delete affordances when `kind !== 'user'`.
- Deletes are soft. Removing an album also removes its images.

| Path | Body | `output` |
| --- | --- | --- |
| `/account/gallery/albums/list` | `{}` | `{ albums: AlbumSummary[] }` |
| `/account/gallery/albums/get` | `{ albumId }` | `AlbumDetail` |
| `/account/gallery/albums/create` | `{ name, description?, visibility? }` | `AlbumInfo` |
| `/account/gallery/albums/update` | `{ albumId, ...partial }` | `AlbumInfo` |
| `/account/gallery/albums/remove` | `{ albumId }` | `null` |
| `/account/gallery/albums/list-public` | `{ accountId }` | `{ albums: AlbumSummary[] }` |
| `/account/gallery/images/upload-intent` | `{ contentType, albumId? }` | `UploadIntent` |
| `/account/gallery/images/confirm` | `{ imageId, width?, height?, ... }` | `GalleryImage` |
| `/account/gallery/images/update` | `{ imageId, ...partial }` | `null` |
| `/account/gallery/images/remove` | `{ imageId }` | `null` |

```ts
export interface AlbumInfo {
  albumId: string;
  name: string;
  description: string;
  kind: AlbumKind;
  visibility: AlbumVisibility;
  coverImageId: string | null;
}

export interface AlbumSummary extends AlbumInfo {
  imageCount: number;
  coverUrl: string | null;   // presigned, expires
}

export interface GalleryImage {
  imageId: string;
  albumId: string;
  status: ImageStatus;
  url: string;               // presigned, expires
  contentType: string;
  sizeBytes: number | null;
  width: number | null;
  height: number | null;
  caption: string | null;
  cityName: string | null;
  latitude: number | null;
  longitude: number | null;
  sortOrder: number;
}

export interface AlbumDetail extends AlbumInfo { images: GalleryImage[]; }

export interface UploadIntent {
  imageId: string;
  albumId: string;
  uploadUrl: string;
  expiresIn: number;         // seconds
}
```

`albums/update` accepts `coverImageId`, but the image must already belong to that album — a
mismatch returns 422. Send `"coverImageId": null` to clear it.

`images/update` moves an image between albums via `albumId`. Omit the key to leave it in place.

---

## 6. Upload flow

Three steps. Step 2 goes **directly to S3**, not to our API.

```ts
export async function uploadImage(file: File, token: string, albumId?: string) {
  // 1. Reserve an image id and get a presigned PUT URL.
  const intent = await apiPost<UploadIntent>(
    '/account/gallery/images/upload-intent',
    { contentType: file.type, albumId },
    token
  );

  // 2. PUT the bytes straight to storage. No Authorization header here —
  //    the signature is in the URL. Content-Type MUST match what you declared.
  const put = await fetch(intent.uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  });
  if (!put.ok) throw new Error('Upload to storage failed');

  // 3. Confirm. The server HEADs the object to verify type and size.
  const { width, height } = await readDimensions(file);
  return apiPost<GalleryImage>(
    '/account/gallery/images/confirm',
    { imageId: intent.imageId, width, height },
    token
  );
}
```

Rules and gotchas:

- **Allowed types: `image/jpeg`, `image/png`, `image/webp`. Max 10 MB.** Validate client-side
  before step 1 for a fast error; the server enforces it again at step 3.
- **The `Content-Type` on the `PUT` must exactly match the `contentType` you sent to
  `upload-intent`.** The presigned signature covers it; a mismatch makes S3 reject the upload.
- Do **not** attach the `Authorization` header to the S3 `PUT`. Some S3 implementations reject
  requests carrying two auth mechanisms.
- `uploadUrl` expires (`expiresIn`, default 900s). Request a fresh intent if the user stalls.
- **`width`/`height` are supplied by the client and stored as-is** — the server does not open
  the file. Read them from an `Image`/`createImageBitmap` before confirming, or omit them.
- An image is only visible in album listings after step 3. If the user abandons the flow the
  row stays `pending` and is not returned by `albums/get`.
- The API never exposes the storage object key — only presigned `url` values.

### Presigned URLs expire

`profilePictureUrl`, `coverUrl` and `GalleryImage.url` are **short-lived** (default 15
minutes). Do not persist them in a database, a long-lived cache, a CDN, or a static prop.

In Next.js:

- Fetch them **per request** in a Server Component, or client-side via SWR/React Query with a
  `staleTime` well under 15 minutes.
- If using `next/image`, add the S3 host to `images.remotePatterns`. Because the query string
  carries the signature, prefer `unoptimized` or a low `minimumCacheTTL` so Next doesn't serve
  a cached entry keyed on a stale signature.
- On a long-lived page (an album the user leaves open), refetch on window focus so images
  don't silently 403.

---

## 7. Profile picture

The picture is an ordinary gallery image that must live in the `Profile` album.

```ts
// Reuse a previous picture
await apiPost('/account/profile/picture/set', { imageId }, token);

// Upload a new one, then set it
const profileAlbum = albums.find((a) => a.kind === 'profile')!;
const image = await uploadImage(file, token, profileAlbum.albumId);
await apiPost('/account/profile/picture/set', { imageId: image.imageId }, token);

await apiPost('/account/profile/picture/clear', {}, token);
```

`picture/set` returns 422 if the image is not confirmed (`status !== 'ready'`), not owned by
the caller, or not in the `Profile` album. A natural UI is a picker showing the `Profile`
album's images plus an "upload new" tile.

Removing an image that is the current profile picture clears the picture automatically, and
also clears it from any album cover.

---

## 8. Public albums

`albums/list-public` takes **another account's** `accountId` and returns only that account's
albums with `visibility: "public"`. It requires a valid token but no ownership. Everything
else in the gallery is strictly owner-scoped.

There is currently no endpoint to look up an account by handle or username, so you need the
`accountId` from elsewhere before this is useful.

---

## 9. Suggested Next.js wiring

- **One profile query key.** Since every section update returns the full `AccountProfile`,
  invalidate/replace a single `['account-profile']` entry rather than per-section keys.
- **Optimistic UI is safe for toggles** (preferences) because the server echoes the full
  object back; reconcile on response.
- **Server Components** can render the profile, but remember the presigned URLs — fetch on
  each request, don't cache the page containing them.
- **Route handlers as a proxy** are a good idea if you keep the access token in an httpOnly
  cookie: expose `/api/profile/*` in Next, attach the bearer token server-side, and forward.
  The S3 `PUT` must still go directly from the browser.

---

## 10. Known limitations

- Email changes are not verified.
- No thumbnails or resized variants — you receive originals, so constrain rendering yourself.
- No pagination on album or image listings.
- No caps on the number of albums, images, travellers, or list entries.
- `location` and the five destination lists are free text today. A place catalog is planned;
  the request shape will not change, but IDs may be added alongside the text.
- No admin-facing view of these profiles yet.
