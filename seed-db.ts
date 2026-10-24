import "dotenv/config";
import { MongoClient } from "mongodb";
import {
  novaTutors,
  sarahJohnson,
  rachelThompson,
  jamesCarter,
} from "./lib/demoData.js";

const uri = process.env.MONGODB_URI;

if (!uri) {
  throw new Error("MONGODB_URI is missing");
}

const client = new MongoClient(uri);

async function seedDatabase() {
  try {
    await client.connect();

    const db = client.db("nova");

    console.log("✅ Connected to Nova database");
    const businesses = db.collection("businesses");

await businesses.updateOne(
  { id: novaTutors.id },
  { $set: novaTutors },
  { upsert: true }
);

console.log("✅ Nova Tutors saved");

const leads = db.collection("leads");

await leads.updateOne(
  { id: sarahJohnson.id },
  { $set: sarahJohnson },
  { upsert: true }
);

await leads.updateOne(
  { id: rachelThompson.id },
  { $set: rachelThompson },
  { upsert: true }
);

await leads.updateOne(
  { id: jamesCarter.id },
  { $set: jamesCarter },
  { upsert: true }
);

console.log("✅ Sarah, Rachel and James saved");

  } catch (error) {
    console.error("❌ Failed to seed database:");
    console.error(error);
  } finally {
    await client.close();
  }
}

seedDatabase();