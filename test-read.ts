import "dotenv/config";
import { MongoClient } from "mongodb";

const uri = process.env.MONGODB_URI;

if (!uri) {
  throw new Error("MONGODB_URI is missing");
}

const client = new MongoClient(uri);

async function readLeads() {
  try {
    await client.connect();

    const db = client.db("nova");
    const leads = db.collection("leads");

    const savedLeads = await leads.find({}).toArray();

    console.log(savedLeads);
  } catch (error) {
    console.error("❌ Failed to read leads:");
    console.error(error);
  } finally {
    await client.close();
  }
}

readLeads();