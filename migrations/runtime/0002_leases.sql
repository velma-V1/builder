CREATE TABLE fencing_counters (
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    last_token INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (resource_type, resource_id)
);

CREATE TABLE leases (
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    owner_id TEXT NOT NULL,
    process_epoch TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    released INTEGER NOT NULL DEFAULT 0 CHECK (released IN (0, 1)),
    PRIMARY KEY (resource_type, resource_id, fencing_token)
);
