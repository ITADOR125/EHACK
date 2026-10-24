import type { Business } from "./models.js";

export const novaTutors: Business = {
  id: "nova-tutors",
  name: "Nova Tutors",

  services: [
    {
      name: "GCSE Maths Tutoring",
      price: 30,
      priceUnit: "hour",
    },
  ],

  tone: "friendly, supportive and professional",

  restrictions: [
    "Do not guarantee specific grade improvements",
    "Do not invent information about the tutoring service",
  ],

  qualificationRules: {
    requiredFields: [
      "subject",
      "year",
      "currentGrade",
      "targetGrade",
      "examBoard",
      "tier",
    ],
  },
};

import type { Lead } from "./models.js";

export const sarahJohnson: Lead = {
  id: "sarah-johnson",
  businessId: "nova-tutors",

  name: "Sarah Johnson",

  student: {
    name: "Daniel",
  },

  need: "GCSE Maths tutoring",
  subject: "Maths",
  year: "Year 11",

  currentGrade: null,
  targetGrade: null,
  examBoard: null,
  tier: null,
  location: null,
  preferredFormat: null,

  status: "new",
  nextAction: "analyse_lead",
};

export const rachelThompson: Lead = {
  id: "rachel-thompson",
  businessId: "nova-tutors",

  name: "Rachel Thompson",

  student: {
    name: "Oliver Thompson",
  },

  need: "GCSE Mathematics tutoring",
  subject: "Maths",
  year: "Year 10",

  currentGrade: 5,
  targetGrade: 7,
  examBoard: "Edexcel",
  tier: null,
  location: "Islington, London",
  preferredFormat: "1-to-1 online tutoring",

  status: "new",
  nextAction: "analyse_lead",
};

export const jamesCarter: Lead = {
  id: "james-carter",
  businessId: "nova-tutors",

  name: "James Carter",

  student: {
    name: "James Carter",
  },

  need: "University Mathematics tutoring",
  subject: "University Mathematics",
  year: "First-year university",

  currentGrade: null,
  targetGrade: null,
  examBoard: null,
  tier: null,
  location: "Camden, London",
  preferredFormat: "1-to-1 online tutoring",

  status: "new",
  nextAction: "analyse_lead",
};