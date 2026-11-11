// Static imports give each photo its size and a tiny blurred preview at build
// time, so a hero shows the blurred photo at once while the real one loads.
import about from "../../../public/images/about.webp";
import contact from "../../../public/images/contact.webp";
import home from "../../../public/images/home.webp";
import lms from "../../../public/images/lms.webp";
import pricing from "../../../public/images/pricing.webp";

export const HERO_IMAGES = { home, about, lms, pricing, contact };

/** Same `sizes` everywhere, so preloaded files are the ones the heroes ask for. */
export const HERO_SIZES = "100vw";
