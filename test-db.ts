import "dotenv/config";
import { MongoClient } from "mongodb";

const uri = process.env.MONGODB_URI;

if (!uri) {
  throw new Error("MONGODB_URI is missing");
}

const client = new MongoClient(uri);

async function testConnection() {
  try {
    await client.connect();
    await client.db("admin").command({ ping: 1 });

    console.log("✅ Connected to MongoDB Atlas successfully!");
  } catch (error) {
    console.error("❌ MongoDB connection failed:");
    console.error(error);
  } finally {
    await client.close();
  }
}

testConnection();