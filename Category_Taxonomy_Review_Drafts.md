# Category Taxonomy: Decisions and Review Drafts

**Status:** Draft for review (2026-10-25). Nothing in `user-stories.md`, the LLDs or the HLDs has been changed yet.
**Sources:** `Documents/Category_Taxonomy_CSVs/*` (README, Taxonomy, Common Metadata, Metadata Profiles, Metadata Dictionary, Restrictions, Real-Estate UX Model) and `ValueX_Category_Taxonomy_MVP_Design.md` (ideas for tables and endpoints only; where it conflicts with our design, our design wins).

---

## 1. Decisions log (all confirmed by you)

| # | Decision |
|---|---|
| D1 | Multi-category tagging is dropped. A listing has exactly one L3 category. L1 and L2 are derived. US-006 is rewritten and implemented first. |
| D2 | Existing tables and endpoints are evolved in place by migration (for example `category_slug` becomes an L3 category id). The design document's `listing`, `listing-drafts` and `/publish` names are not used. Existing lifecycle (plan selection, payment, Trust & Safety review) stays. |
| D3 | Only the Item Details page changes in the seller flow: required and optional metadata fields per category. Aadhaar after submit, plan selection and the rest stay as they are. |
| D4 | AI is switched on or off by an Admin. When on, available and confident, AI prefills fields. Otherwise the seller enters all fields (including the category) by hand. |
| D5 | Photo search stays premium. pgvector is dropped for MVP; use valuex-ai Vision plus OpenSearch. Retention and limits for seller and buyer photos are defined in the respective stories. |
| D6 | Restrictions: AI and keyword detection. Prohibited items are blocked. A Conditional category shows a compliance popup (Restrictions sheet text); the seller continues only if they agree. |
| D7 | Condition scale stays NEW, LIKE_NEW, GOOD, FAIR, POOR. Photos stay 2 to 10. |
| D8 | Item location and its public precision are handled by updating US-108. |
| D9 | Search ranking follows the HLD. The OpenSearch listing document is updated to carry plan type, seller rating and so on. |
| D10 | Common fields appear only where they make sense (for example `delivery_modes` is not shown for Real Estate or whole vehicles). `negotiable` is a new required field and does not replace today's negotiation note. |
| D11 | Real estate pricing: one normalized `listing_price_inr`, derived per intent. Sale uses `sale_price` (`price_min` for New Developments, shown as "Starting from"). Rent and Lease use `monthly_rent`. `lease_amount` (total lease amount, optional) is added to `PROP_COMMERCIAL`. `monthly_rent` is added to `PROP_LAND` (needed because Land Lease uses it). Real Estate does not use `asking_price_inr`. |
| D12 | Real Estate search always runs within a transaction intent. The buyer uses text search and filters (Buy, Rent or Lease; residential or commercial and so on). The intent filter is mandatory before any price range or sort. |
| D13 | Supported intents per property family: Homes Sale/Rent, New Developments Sale only, Land Sale/Lease, Commercial Sale/Rent/Lease, Shared Rent only. The seller is asked Sale/Rent/Lease on Item Details. Transaction intent is a column on the listing. |
| D14 | Property listings follow plans that will differ by L1 (new story). Until then they use the current plan, and a banner "Plan is under revision until US-119" shows for all categories in Dev only. |
| D15 | "Others": when AI cannot categorize an item, or the category does not exist or is disabled, the listing falls in "Others" (the L2's "Other ..." L3 when the L2 is known, otherwise the L1 "Other") and the seller corrects it by hand. For "Others" items all non-common attributes go into `special_attributes_json`. |
| D16 | No general public/private attribute flag. Two sheet notes are fixed rules: `seller_location_pincode` is not public, and the value of `serial_number_present` is protected. |
| D17 | Delivery-eligible categories capture the packed weight and size on Item Details using Common `weight_kg` and `dimensions_cm`, required there. |
| D18 | Property flow after discovery covers chat, calls and video calls, and price negotiation. It ends when the seller marks the property sold or rented. No cart, escrow or delivery. |
| D19 | Prohibited-item popup text is shown only on detection (the block). It is not an attestation shown to every seller. |
| D20 | Attribute definitions and options are editable by Admins at runtime, including bulk upload of options. Category updates and the AI enable/disable switch live in the Admin UI. |
| D21 | Taxonomy importer: CSVs committed under `valuex-backend/src/main/resources/taxonomy/`, Flyway for schema, an idempotent all-or-nothing importer (dry run, hierarchy and key validation, popular limits 15 L1 and 10 L2 per L1, checksum log) run on deploy and from an admin trigger later. Dev data is discarded. |
| D22 | OpenSearch gets its own story. Shiprocket gets its own story, with your delivery items 20 to 26 as open items. |
| D23 | The Metadata Dictionary is authoritative for the 492 keys: `Attribute Key` is the stable identifier, `Display Name` is the UI label. Data type, UI control, search/filter flags and AI extractability are defaults that profile or category configuration may override. |
| D24 | A Real Estate search without a chosen intent prompts the buyer to choose Buy, Rent or Lease before prices are shown. `monthly_rent` is added to `PROP_LAND` (confirmed). |
| D25 | The Real Estate compliance popup applies to all 37 Real Estate L3 categories, although the taxonomy marks only the 7 New Developments L3 as Conditional. |
| D26 | The maximum price is raised from ₹1,00,00,000 to ₹10,00,00,000 (10 crore) for every category. |
| D27 | Attributes that repeat the L3 name (`property_type`, `commercial_type`, `land_type`, `development_type`, `accommodation_type`, and similar) are filled from the L3 category and not asked again. |
| D28 | The required-fields table, option lists, type corrections, validation ranges and the five new story drafts have been reviewed by you. |
| D29 | Solar Panels (CAT-0204) and Forklifts (CAT-0742) get no compliance popup. The mappings of Electric Toothbrushes, Breast Pumps and Vintage / Classic Cars are confirmed. |
| D30 | US-006 is 13 SP. Real Estate and Conditional categories are enabled from day one (no feature flags), because the project is still in development. Because of that, seller-side transaction intent and the `listing_price_inr` derivation (D11) are built in US-006 so Real Estate listings are not left without a price. |
| D31 | All optional Common fields go under "More details": `age_months`, `purchase_year`, `original_price_inr`, `invoice_available`, `warranty_status`, `warranty_end_date`, `repair_history`, `ownership_count`, `serial_number_present`, `video_available`, `authenticity_proof` (not for Real Estate). `video_available` stays hidden until video upload is supported. |
| D32 | The existing `price` column and API field keep their names and hold the normalized listing price. |
| D33 | Option-list batch 2 (section 8) is reviewed and approved. The US-006 implementation plan is approved. |

---

## 2. Common fields: where they apply

| Field | Goods | Cars, Motorcycles, Commercial vehicles | Real Estate |
|---|---|---|---|
| title, description, photos, category (L3) | Required | Required | Required |
| `condition_grade`, `condition_notes` | Required | Required | Not shown |
| `listing_price_inr` | From `asking_price_inr` | From `asking_price_inr` | Derived (D11) |
| `negotiable` | Required | Required | Required for Homes, Commercial, Land (as in the dictionary) |
| `quantity` | Required | Not shown (always 1) | Not shown |
| `delivery_modes`, packed `weight_kg` and `dimensions_cm` | Shown and required only for delivery-eligible L3 | Not shown (self-pickup only) | Not shown |
| Location | `seller_location_city` and pincode (from the US-108 address) | Same | Property's own city, locality, pincode (profile fields) |
| Optional Common fields, all under "More details" (`age_months`, `purchase_year`, `original_price_inr`, `invoice_available`, `warranty_status`, `warranty_end_date`, `repair_history`, `ownership_count`, `serial_number_present`, `video_available`, `authenticity_proof`) | Optional | Optional | Not shown |

---

## 3. Draft: required fields per profile

Everything else in a profile is optional. "AI" means the dictionary marks the field AI-extractable (Yes or Limited), so AI may prefill it only when visible in photos. Fields that are not visible are never inferred.

| Profile | Required fields |
|---|---|
| APPAREL | apparel_type, gender, size_label, color |
| AUDIO | audio_type, brand |
| BABY_GEAR | item_type, brand |
| BAG | bag_type |
| BEAUTY | product_type, brand, sealed_flag, expiry_date |
| BICYCLE | cycle_type, brand, electric_flag |
| BOOK | item_type, title_or_product_name, language |
| CAMERA | camera_type, brand, model |
| CAM_ACC | accessory_type, brand |
| CAR | make, model, manufacture_year, fuel_type, transmission, odometer_km, owner_count, registration_state |
| COLLECTIBLE | collectible_type, title_or_subject |
| COMM_VEHICLE | make, model, vehicle_type, manufacture_year, fuel_type, odometer_km_or_hours |
| COMPUTER | form_factor, brand, processor_model, ram_gb, storage_gb |
| CRAFT | craft_type, product_type |
| FESTIVE | item_type, occasion_or_festival |
| FOOTWEAR | footwear_type, gender, brand, size_india |
| FURNITURE | furniture_type, material |
| GAMING | platform, brand |
| GARDEN | item_type |
| GROCERY | product_type, brand, sealed_flag, expiry_date |
| HOME_DECOR | item_type |
| INDUSTRIAL | equipment_type, brand, working_status, manufacture_year |
| KITCHEN | item_type |
| LAPTOP | brand, model, processor_model, ram_gb, storage_gb, screen_size_in |
| LARGE_APPLIANCE | appliance_type, brand, working_status |
| LENS | brand, lens_mount, focal_length_mm |
| MEDICAL | device_type, brand, intended_use, working_status |
| MOBILE_ACC | accessory_type |
| MONITOR | brand, screen_size_in, resolution |
| MUSIC | instrument_family, instrument_type, brand |
| OFFICE | equipment_type, brand |
| OTHER | item_type_free_text |
| PC_ACC | device_type, brand |
| PC_COMPONENT | component_type, brand |
| PET | pet_type, product_type |
| PHONE | brand, model, storage_gb |
| SMALL_APPLIANCE | appliance_type, brand, working_status |
| SPORTS | sport, equipment_type |
| TABLET | brand, model, storage_gb |
| TOOL | tool_type, brand, working_status |
| TOY | toy_type, age_range |
| TV | brand, display_type, screen_size_in |
| TWOWHEELER | make, model, vehicle_type, manufacture_year, odometer_km, owner_count |
| VEHICLE_PART | vehicle_type, part_type |
| WATCH_JEWEL | item_type |
| WEARABLE | wearable_type, brand |
| PROP_HOME | transaction_intent, property_type\*, city, locality, pincode, bedrooms_bhk, bathrooms, carpet_area_sqft, furnishing_status, availability_status, ownership_type, listing_party, price by intent |
| PROP_NEW_DEV | transaction_intent (Sale only), development_type\*, project_name, developer_name, city, locality, pincode, price_min, launch_status, construction_stage, possession_date, rera_id, listing_party |
| PROP_LAND | transaction_intent, land_type\*, city, locality, pincode, plot_area, plot_area_unit, ownership_type, listing_party, price by intent |
| PROP_COMMERCIAL | transaction_intent, commercial_type\*, city, locality, pincode, carpet_area_sqft, furnishing_status, listing_party, price by intent |
| PROP_SHARED | accommodation_type\*, city, locality, pincode, sharing_type, monthly_rent, security_deposit, gender_preference, available_from, listing_party |

\* Duplicates the L3 category (for example Apartment, Villa, Plot). Proposed: fill it from the L3 category and do not ask the seller again. The same applies to other "type" attributes that repeat the L3 name (confirmed, decision D27).

**Profile configuration changes (from your decisions):**
- Add `lease_amount` (DECIMAL, INR, optional, total lease amount) to `PROP_COMMERCIAL`.
- Add `monthly_rent` (DECIMAL, INR) to `PROP_LAND`, required when intent is Lease.
- Add a per-profile option list for `transaction_intent`: PROP_HOME Sale/Rent, PROP_NEW_DEV Sale, PROP_LAND Sale/Lease, PROP_COMMERCIAL Sale/Rent/Lease, PROP_SHARED Rent.
- `listing_price_inr` rule: Sale gives `sale_price` (`price_min` for PROP_NEW_DEV), Rent and Lease give `monthly_rent`.

---

## 4. Draft: starter option lists

Brand, model and long-tail lists are not drafted here; they come in through the Admin bulk upload (D20). The lists below cover the shared and high-use options. Per-profile overrides are allowed.

| Attribute | Starter options |
|---|---|
| condition_grade | NEW, LIKE_NEW, GOOD, FAIR, POOR (labels: Brand New, Like New, Good, Fair, Poor) |
| working_status | Fully working, Partially working, Not working, Not applicable |
| warranty_status | In warranty, Out of warranty, No warranty, Unknown |
| delivery_modes | Home delivery, Self pickup |
| authenticity_proof | Invoice, Certificate, Serial number, None |
| transaction_intent | SALE, RENT, LEASE (per-profile subsets above) |
| listing_party | Owner, Agent / Broker, Builder / Developer |
| furnishing_status | Unfurnished, Semi-furnished, Fully furnished |
| availability_status | Ready to move, Available from a date, Under construction |
| fuel_type | Petrol, Diesel, CNG, LPG, Electric, Hybrid |
| transmission | Manual, Automatic |
| network_generation | 4G, 5G |
| ram_gb | 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128 |
| storage_gb | 16, 32, 64, 128, 256, 512, 1024, 2048 |
| storage_type | HDD, SSD, SSD + HDD, eMMC |
| gender | Men, Women, Unisex, Boys, Girls |
| size_label | XS, S, M, L, XL, XXL, 3XL, Free size |
| sleeve_length | Sleeveless, Short, Three-quarter, Full |
| facing | North, South, East, West, North-East, North-West, South-East, South-West |
| plot_area_unit | sq ft, sq yd, sq m, acre, cent, guntha |
| sim_type | Single SIM, Dual SIM, eSIM, Dual SIM + eSIM |
| charging_port_type | USB-C, Lightning, Micro-USB, Proprietary |
| carrier_lock | Unlocked, Locked, Unknown |
| wireless_standard | Wi-Fi 4, Wi-Fi 5, Wi-Fi 6, Wi-Fi 6E, Wi-Fi 7, Bluetooth 4.x, Bluetooth 5.x |
| registration_state | The 28 states and 8 union territories |
| energy_rating | 1 star to 5 star |
| language | English, Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Other |

All other OPTION attributes are covered in section 8 (batch 2).

---

## 5. Draft: data-type corrections and type mapping

**Corrections (profile overrides, dictionary defaults stay as published):**

| Key | Dictionary type | Proposed | Why |
|---|---|---|---|
| wireless_standard | BOOLEAN | OPTION | A standard such as Wi-Fi 6, not yes/no |
| plot_area_unit | DECIMAL | OPTION | A unit (sq ft, acre) |
| size_label | DECIMAL | OPTION | S, M, L labels |
| sleeve_length | DECIMAL | OPTION | Short, Full and so on |
| length (APPAREL) | DECIMAL | OPTION | Crop, Regular, Long |
| paper_size | DECIMAL | MULTI_OPTION | A4, A3, Legal |
| breed_size | DECIMAL | OPTION | Small to Giant |
| pet_weight_range, rider_height_range, age_range_months | DECIMAL | OPTION | Ranges, not single numbers |
| speed_or_modes | DECIMAL | TEXT | Modes are not numeric |
| washrooms | TEXT | INTEGER | A count |
| property_age_years | TEXT | INTEGER (years) | A number |
| facing, sim_type, charging_port_type, carrier_lock, registration_state | TEXT | OPTION | Fixed choices |
| microwave_safe | TEXT | BOOLEAN | Same as `dishwasher_safe` |
| dimensions (COLLECTIBLE, FESTIVE, INDUSTRIAL, OTHER, SPORTS) | OPTION | OBJECT (L x W x H, cm) | Matches `dimensions_cm` |
| weight (SPORTS) | DECIMAL, no unit | DECIMAL, kg | Missing unit |
| frame_size (BICYCLE), speed (PC_COMPONENT) | DECIMAL, no unit | add unit (cm, MHz) | Missing unit |
| pack_size (BOOK) | DECIMAL | INTEGER | A count |

**Mapping of dictionary types the design document lacks:**

| Dictionary type | Stored as |
|---|---|
| OPTION_OR_TEXT | An option, or free text when the attribute allows custom values |
| OBJECT (`dimensions_cm`) | JSON validated against a fixed schema |
| JSON (`special_attributes_json`) | JSONB, used only for "Others" items (D15) |
| UUID, DATETIME | System columns (`listing_id`, `created_at`), not form fields |
| TEXT_LIST (`search_keywords`) | System text array built from AI and seller keywords |

System and column fields, not form attributes: `listing_id`, `created_at`, `title`, `description`, `asking_price_inr`, `listing_price_inr`, `category_l1` to `category_l3` (derived from the L3), `ai_category_confidence`, `ai_condition_confidence`, `search_keywords`.

---

## 6. Draft: default validation ranges

| Rule | Default |
|---|---|
| Text | Title max 100, description max 2000 (existing) |
| INTEGER and DECIMAL | Not negative unless stated |
| Percentages (`battery_health_pct`) | 0 to 100 |
| Years (`manufacture_year`, `registration_year`, `purchase_year`) | 1900 to current year (+1 for manufacture year) |
| `pincode` | 6 digits, first digit 1 to 9 |
| `bedrooms_bhk` | 0 to 20 (0 = studio / 1 RK) |
| `bathrooms`, `balconies`, `parking_count` | 0 to 50 |
| `carpet_area_sqft`, `builtup_area_sqft` | 10 to 10,000,000; built-up at least carpet |
| `floor_number` | -2 to 200; `total_floors` at least `floor_number` |
| `price_min` at most `price_max`; `carpet_area_min_sqft` at most `carpet_area_max_sqft` | Cross-field |
| `players_min` at most `players_max`; `pieces_missing` at most `pieces_total` | Cross-field |
| `odometer_km` | 0 to 1,000,000; `owner_count` 1 to 10 |
| `expiry_date` | Must not be in the past for sealed or consumable items |
| `available_from` | Today or later |
| `quantity` | 1 to 1000 |
| Price | Greater than 0 and at most ₹10,00,00,000 (10 crore) for every category (raised from ₹1,00,00,000, decision D26) |

---

## 7. Draft: Conditional categories mapped to Restrictions rows

Popup text is the Restrictions sheet's "User Popup Message"; the seller continues only on "Agree & Continue". Acceptance is stored with the listing, category, policy version and time. Prohibited rows are used only for the detection block (D19).

| Restrictions row | Conditional L3 categories |
|---|---|
| Opened cosmetics, skincare, fragrances, personal hygiene | All BEAUTY Conditional L3 (Face, Lip, Eye, Nail Makeup; Face, Body, Sun Care; Shampoo and Conditioner, Hair Oils and Serums, Hair Styling; Perfumes, Attars, Deodorants and Body Mists) and, confirmed (D29), Electric Toothbrushes (CAT-0506) |
| Food, pet food, household consumables | Dog Food, Cat Food, Treats, Dry Fruits and Nuts, Spices and Masalas, Tea and Coffee, Snacks and Biscuits, Chocolates and Candies, Cleaning, Laundry and Dishwashing Supplies |
| High-value jewellery, luxury watches, collectibles | Luxury Watches, Gold, Silver, Diamond and Gemstone Jewellery, Coins and, confirmed (D29), Vintage / Classic Cars |
| Medical equipment | Blood Pressure Monitors, Glucometers, Pulse Oximeters, Thermometers, Nebulizers, Oxygen Concentrators, CPAP / BiPAP, TENS Units and, confirmed (D29), Breast Pumps |
| Drones | Camera Drones, Drone Accessories |
| Used helmets, child car seats, safety equipment | Baby Car Seats, Helmets and Riding Gear, Helmets (Bicycles) |
| Large batteries / lithium power packs | E-bikes, Electric Kick Scooters |
| Plants and seeds | Live Plants, Seeds and Bulbs |
| Real estate / property | All 37 Real Estate L3 categories (decision D25); the taxonomy marks only the 7 New Developments L3 as Conditional |
| No matching row (decided, D29: no popup) | Solar Panels (CAT-0204): Policy / Capture Notes say "Electrical installation and warranty transfer should be captured". Forklifts (CAT-0742): "Ownership and safety verification required" |

AI and keyword detection can also trigger a row's popup on a listing whose category is not Conditional.

---

## 8. Draft: option lists, batch 2 (for your review)

Every OPTION, MULTI_OPTION and OPTION_OR_TEXT attribute in the dictionary falls into one of three groups. Per-profile subsets use `profile_attribute_options`.

### 8.1 Generated from L3 names at import (no list to maintain)
These "type" attributes repeat what the L3 category already says (D27). The importer builds each profile's options from the distinct L3 names under it and pre-fills the value from the chosen L3. The seller can change it only where the L3 is broader than the type.

`property_type`, `commercial_type`, `land_type`, `development_type`, `accommodation_type`, `apparel_type`, `footwear_type`, `bag_type`, `camera_type`, `wearable_type`, `appliance_type`, `component_type`, `furniture_type`, `tool_type`, `toy_type`, `device_type`, `accessory_type`, `collectible_type`, `craft_type`, `audio_type`, `equipment_type`, `item_type`, `part_type`, `product_type`, `instrument_type`, `instrument_family` (from the L2), `cycle_type`, `lens_type`.

### 8.2 Fixed lists drafted here

| Attribute | Options |
|---|---|
| acoustic_or_electric | Acoustic, Electric, Semi-acoustic, Digital |
| age_group | Newborn, Infant, Toddler, Kids, Teen, Adult |
| age_range (TOY) | 0-1 yr, 1-3 yrs, 3-5 yrs, 5-8 yrs, 8-12 yrs, 12+ yrs, All ages |
| age_range_months (BABY_GEAR) | 0-6, 6-12, 12-24, 24-36, 36+ months |
| board_or_exam | CBSE, ICSE, ISC, State board, IB, Cambridge (IGCSE), NEET, JEE, UPSC, GATE, CAT, SSC, Banking, CA / CS / CMA, Other |
| body_type (CAR) | Hatchback, Sedan, SUV, MUV / MPV, Coupe, Convertible, Pickup, Van, Station wagon |
| brake_type | Rim, Disc (mechanical), Disc (hydraulic), Drum, Coaster |
| certification (INDUSTRIAL) | CE, ISI, BIS, ISO 9001, UL, ATEX, None |
| certification (WATCH_JEWEL) | BIS hallmark, GIA, IGI, SGL, HRD, Other, None |
| channel_configuration | Mono, Stereo, 2.1, 5.1, 7.1, Dolby Atmos |
| class_level | Nursery, KG, Class 1 to Class 12, Undergraduate, Postgraduate, Competitive exam, Professional |
| configuration_bhk | Studio, 1 RK, 1 BHK, 1.5 BHK, 2 BHK, 2.5 BHK, 3 BHK, 3.5 BHK, 4 BHK, 5 BHK, 6+ BHK |
| connectivity | Wired, Bluetooth, Wi-Fi, Wi-Fi + Bluetooth, USB, NFC, Cellular (4G / 5G); TABLET subset: Wi-Fi only, Wi-Fi + Cellular |
| connector_type | USB-C, Lightning, Micro-USB, USB-A, 3.5 mm, MagSafe, Wireless (Qi), Proprietary, Other |
| construction_stage | Not started, Foundation, Structure, Finishing, Ready for possession |
| display_type (TV) | LED, OLED, QLED, Mini-LED, LCD, Plasma, Projector (DLP), Projector (LCD), Projector (Laser) |
| edition | Standard, Deluxe, Collector's, Limited, Bundle, First edition, Revised edition, International edition, Other |
| educational_skill | STEM, Language, Maths, Motor skills, Creativity, Problem solving, Social skills, None |
| era | Antique (100+ years), Vintage (50 to 99 years), Mid-century, Retro (20 to 49 years), Modern |
| fabric | Cotton, Linen, Silk, Wool, Polyester, Nylon, Denim, Viscose / Rayon, Georgette, Chiffon, Velvet, Leather, Blend, Other |
| fit | Slim, Regular, Relaxed, Oversized, Skinny, Tailored, Straight |
| form_factor (COMPUTER) | Tower, Mini tower, Small form factor, All-in-one, Mini PC, Workstation, Thin client |
| frame_material | Steel, Aluminium, Carbon fibre, Alloy, Titanium, Other |
| gears | Single speed, 3, 6, 7, 8, 9, 10, 11, 12, 18, 21, 24, 27 |
| gender_preference | Male, Female, Any |
| genre | Fiction, Non-fiction, Fantasy, Sci-fi, Mystery / Thriller, Romance, Biography, Self-help, History, Comics / Graphic, Children's, Poetry, Religion / Spirituality, Business, Cooking, Travel, Other |
| industry | Manufacturing, Construction, Agriculture, Food processing, Textile, Pharma, Hospitality, Retail, Printing, Packaging, Mining, Automotive, Other |
| intended_use | Home use, Clinical / professional use, Diagnostic, Therapy, Mobility aid, Office, Industrial, Personal, Other |
| interface | USB-A, USB-C, Ethernet, Wi-Fi, Bluetooth, HDMI, DisplayPort, Serial, Parallel, Other |
| launch_status | Upcoming, Pre-launch, Newly launched, Ongoing sales, Ready to move, Sold out |
| lens_mount, mount (CAMERA) | Canon EF, Canon EF-S, Canon RF, Nikon F, Nikon Z, Sony E, Sony A, Fujifilm X, Micro Four Thirds, Leica L, Pentax K, M42, Other |
| max_aperture | f/0.95, f/1.2, f/1.4, f/1.8, f/2, f/2.8, f/3.5, f/4, f/4.5, f/5.6, f/6.3, Variable |
| metal_type | Gold, Silver, Platinum, Rose gold, White gold, Copper, Brass, Stainless steel, Other |
| movement_type | Quartz, Automatic, Mechanical (manual), Smart / digital, Solar, Kinetic |
| noise_cancellation | None, Passive, Active, Adaptive / Hybrid |
| occasion | Casual, Formal, Party, Wedding, Festive, Sports / Active, Work, Travel, Lounge / Night |
| occasion_or_festival | Diwali, Holi, Eid, Christmas, Navratri, Durga Puja, Ganesh Chaturthi, Raksha Bandhan, Onam, Pongal, Wedding, Birthday, Housewarming, General |
| os | PHONE: Android, iOS; LAPTOP / COMPUTER: Windows, macOS, Linux, ChromeOS, No OS; TV: Android TV, Google TV, Tizen, webOS, Fire TV, Other; TABLET: Android, iPadOS, Windows, Fire OS |
| ownership_type | Freehold, Leasehold, Co-operative society, Power of attorney, Other |
| panel_type | IPS, VA, TN, OLED, Mini-LED, QLED, LED, Other |
| parking (PROP_NEW_DEV) | None, Open, Covered, Open + Covered, Basement, Multi-level |
| pattern | Solid, Striped, Checked, Printed, Floral, Geometric, Embroidered, Colour-block, Other |
| pet_type | Dog, Cat, Bird, Fish, Small animal, Reptile, Other |
| platform (GAMING) | PlayStation 5, PlayStation 4, Xbox Series X|S, Xbox One, Nintendo Switch, PC, Android, iOS, VR, Retro, Other |
| processor_brand | Intel, AMD, Apple, Qualcomm, MediaTek, Other |
| purity | Gold: 24K, 22K, 18K, 14K; Silver: 999, 925, 800; Platinum: 950 |
| resolution | HD (1366x768), Full HD (1920x1080), QHD (2560x1440), 4K UHD (3840x2160), 5K, 8K, Other |
| room (HOME_DECOR) | Living room, Bedroom, Kitchen, Dining, Bathroom, Kids room, Study / Office, Outdoor, Entrance, Any |
| sharing_type | Single, Double, Triple, Four or more, Dormitory |
| skill_level | Beginner, Intermediate, Advanced, Professional |
| skin_or_hair_type | Dry, Oily, Combination, Normal, Sensitive, Straight, Wavy, Curly, Coily, All types |
| socket_or_interface | LGA1700, LGA1200, AM4, AM5, PCIe 3.0, PCIe 4.0, PCIe 5.0, SATA, NVMe M.2, DDR4, DDR5, SO-DIMM, Other |
| sport | Cricket, Football, Badminton, Tennis, Basketball, Table tennis, Hockey, Golf, Skating, Boxing / Martial arts, Swimming, Yoga, Gym / Fitness, Cycling, Other |
| stone_type | Diamond, Ruby, Emerald, Sapphire, Pearl, Cubic zirconia, Moissanite, Other gemstone, None |
| style | Modern, Contemporary, Traditional, Classic, Rustic, Industrial, Scandinavian, Minimalist, Bohemian, Vintage |
| subject | Maths, Physics, Chemistry, Biology, English, Hindi, Social science, History, Geography, Economics, Computer science, Engineering, Medicine, Law, Commerce / Accounts, Other |
| technology (OFFICE) | Laser, Inkjet, Ink tank, Thermal, Dot-matrix, LED, Other |
| theme | Religious, Traditional, Modern, Eco-friendly, Kids, Sports, Nature, Other |
| vehicle_type | COMM_VEHICLE: Truck, Mini truck, Tempo, Bus, Mini bus, Tractor, Harvester, Pickup; TWOWHEELER: Motorcycle, Scooter, Moped, Electric scooter, Electric motorcycle; VEHICLE_PART: Car, Motorcycle, Scooter, Bicycle, Truck, Tractor, Other |
| zoning_or_permitted_use | Residential, Commercial, Industrial, Agricultural, Mixed use, Institutional, Recreational |
| color (OPTION_OR_TEXT) | Black, White, Grey, Silver, Gold, Red, Blue, Green, Yellow, Orange, Pink, Purple, Brown, Beige, Multicolour, Other |
| material (OPTION_OR_TEXT) | Wood, Metal, Plastic, Glass, Leather, Fabric, Rubber, Ceramic, Stone, Bamboo, Paper, Other (per-profile subsets) |
| accessories (MUSIC) | Case / Gig bag, Stand, Strap, Cable, Picks, Pedal, Amplifier, Tuner, Sticks, Manual, Other |
| accessories_included | Original box, Charger, Cable, Manual, Remote, Case / Cover, Earphones, Adapter, Warranty card, Other |
| missing_parts | Charger, Cable, Remote, Box, Manual, Screws / Fittings, Batteries, Other |
| amenities (PROP_HOME, PROP_NEW_DEV, PROP_COMMERCIAL, PROP_SHARED) | Lift, Parking, Power backup, Security, CCTV, Gym, Swimming pool, Clubhouse, Park / Garden, Children's play area, 24x7 water supply, Gas pipeline, Intercom, Visitor parking, Fire safety, Rainwater harvesting, Wi-Fi, Air conditioning, Cafeteria, Conference room |
| caps_hood_case_included | Front cap, Rear cap, Hood, Case / Pouch |
| hdr_formats | HDR10, HDR10+, Dolby Vision, HLG |
| ports | HDMI, USB, USB-C, DisplayPort, VGA, DVI, Ethernet, 3.5 mm, Thunderbolt, Optical audio |
| supported_systems | Windows, macOS, Linux, Android, iOS, ChromeOS |
| unit_types (PROP_NEW_DEV) | Studio, 1 BHK, 2 BHK, 3 BHK, 4 BHK, 5+ BHK, Villa, Plot, Shop, Office |
| nearby_landmarks (PROP_LAND) | Metro station, Railway station, Airport, Highway, School, Hospital, Mall, Market, Park, IT park |
| compatible_years | A generated range, 1990 to the current year |

### 8.3 Admin bulk upload (too large or volatile to hard-code)
Until Admin loads options, the field shows as a text field with free-text entry (OPTION_OR_TEXT behaviour).

- **Brand and make:** `brand`, `make` (cars, two-wheelers, commercial vehicles), `compatible_brand`, `compatible_make`, `compatible_camera_system`, `compatible_models`. Suggested starter makes for a first upload: Cars: Maruti Suzuki, Hyundai, Tata, Mahindra, Honda, Toyota, Kia, Renault, Skoda, Volkswagen, Ford, Nissan, MG, Jeep, BMW, Mercedes-Benz, Audi, Volvo. Two-wheelers: Hero, Honda, Bajaj, TVS, Royal Enfield, Yamaha, Suzuki, KTM, Ather, Ola Electric. Commercial and agricultural: Tata Motors, Ashok Leyland, Mahindra, Eicher, BharatBenz, Force, Swaraj, John Deere, Sonalika, Massey Ferguson, Kubota.
- **Hardware models:** `processor_model`, `gpu_model`.
- **Other:** `artist_or_maker`, `compatibility`, `shade` (varies by brand), `size` (differs by profile: PET, MUSIC, SPORTS, CRAFT, CAM_ACC, VEHICLE_PART, WATCH_JEWEL), `capacity` (differs by profile and appliance type).

**Notes on a few attributes**
- `video_available`: hidden until the listing flow supports video upload (decided).
- `serial_number_present`: stored as yes/no only; the serial number value is never stored (D16).
