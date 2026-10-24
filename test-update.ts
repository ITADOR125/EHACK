import "dotenv/config";
import { MongoClient } from "mongodb";

const uri = process.env.MONGODB_URI;

if (!uri) {
  throw new Error("MONGODB_URI is missing");
}

const client = new MongoClient(uri);

async function updateSarah() {
  try {
    await client.connect();

    const db = client.db("nova");
    const leads = db.collection("leads");

    await leads.updateOne(
      { id: "sarah-johnson" },
      {
        $set: {
          currentGrade: 4,
        },
      }
    );

    console.log("✅ Sarah updated");
  } catch (error) {
    console.error("❌ Failed to update Sarah:");
    console.error(error);
  } finally {
    await client.close();
  }
}
updateSarah();