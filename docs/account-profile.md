# Account profile

Customer-facing profile, frequent travellers and image gallery. All endpoints live under
`/v1/account/...`, require an account access token, and are **`POST` only**.

## Update semantics

Every update endpoint is a partial update:

| Request body | Effect |
| --- | --- |
| key absent | field unchanged |
| key present with a value | field set |
| key present as `null` | field cleared |

## Profile fields

| Section | Fields |
| --- | --- |
| Personal | `firstName`, `lastName`, `gender`, `dateOfBirth`, `nationality`, `location`, `language`, `description`, `email`, `facebook`, `instagram`, `linkedin` |
| Contact | `alternativePhone`, `preferredContactMethod`, `emergencyContact` |
| Preferences | five stay toggles, `flightClass`, `flightPriority`, `tripPace`, `baggageStyle` |
| Destinations | `countriesVisited`, `indianStatesVisited`, `placesLoved`, `placesRecommended`, `travelMomentsEnjoyed` |

Read-only in responses: `dialCode`, `phoneNumber`, `tier`, `badges`, `completionPercentage`,
`profilePictureUrl`. The phone number is the login identity and cannot be changed here.
`tier` and `badges` are assigned by the rewards system.

Defaults on first read: `language=en`, `description=""`, `preferredContactMethod=phone`,
all stay toggles off, `flightClass=economy`, `flightPriority=best_value`, `tripPace=balanced`,
`baggageStyle=light_packer`, `tier=Novus`, `badges=[]`.

`completionPercentage` counts eleven optional fields: first name, last name, gender, date of
birth, nationality, location, description, any social link, alternative phone, emergency
contact, profile picture.

## Location and destination lists

`location` is a free-text city snapshot (`cityName`, `countryCode`, `latitude`, `longitude`)
and the five destination lists are plain string arrays. Both are deliberately denormalized so
a city/place catalog can be introduced later: `location` gains a `cityId` column and the lists
migrate to catalog-referencing rows without changing the request shape.

## Frequent travellers

Date of birth is month and year only (stored as a `DATE` pinned to day 1). Passport numbers
are encrypted at rest and returned masked — see [pii-encryption.md](pii-encryption.md).

## Gallery

Images live in a private S3-compatible bucket. The API never handles image bytes.

1. `POST /account/gallery/images/upload-intent` with `contentType` (and optional `albumId`)
   returns `imageId` and a presigned `PUT` `uploadUrl`.
2. The client `PUT`s the bytes directly to `uploadUrl`.
3. `POST /account/gallery/images/confirm` with `imageId` (plus optional `width`, `height`,
   `caption`, location). The server issues a `HEAD` against the object to verify its
   content type and size before marking the image `ready`.

Allowed types are `image/jpeg`, `image/png`, `image/webp`, up to 10 MB. Reads return
short-lived presigned `GET` URLs; the storage object key is never exposed.

Two system albums are created on first gallery access: `My Photos` (default target for
uploads) and `Profile`. Neither can be renamed or deleted, and only images in `Profile` can be
set as the profile picture. Albums and images are soft-deleted; the S3 object is left in place.

Albums have a `visibility` of `private` (default) or `public`. Public albums are readable by
any authenticated account through `POST /account/gallery/albums/list-public`.

## Required environment

| Variable | Default |
| --- | --- |
| `LTJBE_S3_ENDPOINT_URL` | empty (AWS) |
| `LTJBE_S3_REGION` | `us-east-1` |
| `LTJBE_S3_BUCKET` | `luxtj-dev` |
| `LTJBE_S3_ACCESS_KEY_ID` | empty |
| `LTJBE_S3_SECRET_ACCESS_KEY` | empty |
| `LTJBE_S3_UPLOAD_URL_TTL_SECONDS` | `900` |
| `LTJBE_S3_DOWNLOAD_URL_TTL_SECONDS` | `900` |
