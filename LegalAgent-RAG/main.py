-- contracts
CREATE TABLE contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_name TEXT,
  topic TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- dates
CREATE TABLE contract_dates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID REFERENCES contracts(id),
  start_date DATE,
  end_date DATE,
  renewal_terms TEXT
);

-- clauses
CREATE TABLE contract_clauses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID REFERENCES contracts(id),
  clause_title TEXT,
  clause_summary TEXT
);

-- parties
CREATE TABLE contract_parties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID REFERENCES contracts(id),
  party_role TEXT,
  party_description TEXT
);
