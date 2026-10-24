export interface Service {
  name: string;
  price: number;
  priceUnit: string;
}

export interface Business {
  id: string;
  name: string;
  services: Service[];
  tone: string;
  restrictions: string[];
  qualificationRules: {
    requiredFields: string[];
  };
}

export interface Lead {
  id: string;
  businessId: string;

  name: string;

  student: {
    name: string;
  };

  need: string;
  subject: string;
  year: string;

  currentGrade: number | null;
  targetGrade: number | null;
  examBoard: string | null;
  tier: string | null;
  location: string | null;
  preferredFormat: string | null;

  status: string;
  nextAction: string;
}

export interface Message {
  id: string;
  leadId: string;
  sender: "customer" | "nova" | "owner";
  content: string;
  timestamp: Date;
}

export interface AgentAction {
  id: string;
  leadId: string;
  action: string;
  reason: string;
  status: "completed" | "failed" | "pending";
  timestamp: Date;
}