-- Eyabantu seed data
USE eyabantu;

-- Routes
INSERT INTO routes (name, description) VALUES
('Mamelodi - Pretoria CBD', 'Main route from Mamelodi'),
('Silverton - Pretoria CBD', 'Silverton route'),
('Soshanguve - Pretoria CBD', 'Soshanguve route'),
('Atteridgeville - Pretoria CBD', 'Atteridgeville route'),
('Mabopane - Pretoria CBD', 'Mabopane route'),
('Hammanskraal - Pretoria CBD', 'Hammanskraal route');

-- Stops (route_id matches insertion order)
INSERT INTO stops (name, route_id, distance_to_cbd_km, latitude, longitude) VALUES
('Mamelodi Rank', 1, 2.0, -25.72, 28.35),
('Denneboom', 1, 6.0, -25.70, 28.32),
('Silverton', 2, 7.0, -25.73, 28.30),
('Soshanguve Rank', 3, 4.0, -25.52, 28.10),
('Atteridgeville Rank', 4, 3.0, -25.77, 28.10),
('Mabopane Station', 5, 5.0, -25.50, 28.05),
('Hammanskraal Rank', 6, 8.0, -25.40, 28.27);

-- Demo users (passwords are hashed versions of "demo123" - generate real ones in app)
INSERT INTO users (full_name, email, password_hash, role) VALUES
('Demo Commuter', 'commuter@eyabantu.co.za', 'scrypt:32768:8:1$xAnIasHFICq7Rlhl$52f976df46975df37efaae5a815d2a07dcc9e9f4ce26ceb8250b4ebc565f542e51cc550a8f564ed70a785bfd49f395a91d83e3b8c21bf413b15a4b94f6b39c14', 'commuter'),
('Demo Driver', 'driver@eyabantu.co.za', 'scrypt:32768:8:1$xAnIasHFICq7Rlhl$52f976df46975df37efaae5a815d2a07dcc9e9f4ce26ceb8250b4ebc565f542e51cc550a8f564ed70a785bfd49f395a91d83e3b8c21bf413b15a4b94f6b39c14', 'driver'),
('Demo Association', 'assoc@eyabantu.co.za', 'scrypt:32768:8:1$xAnIasHFICq7Rlhl$52f976df46975df37efaae5a815d2a07dcc9e9f4ce26ceb8250b4ebc565f542e51cc550a8f564ed70a785bfd49f395a91d83e3b8c21bf413b15a4b94f6b39c14', 'association');

-- Sample demand
INSERT INTO demand_reports (stop_id, waiting_passengers, reported_by) VALUES
(1, 210, 1),
(2, 95, 1),
(4, 130, 2);

-- Sample problems
INSERT INTO problem_reports (stop_id, problem_type, description, reported_by) VALUES
(1, 'Taxi is late (ETA wrong)', 'Multiple reports of delay', 1);

-- Sample taxi positions
INSERT INTO taxi_positions (stop_id, driver_id, seats_available, is_active) VALUES
(1, 2, 12, TRUE),
(4, 2, 8, TRUE),
(6, 2, 15, TRUE);

-- Verification reports so some stops show as verified (need 3+ pieces of evidence)
INSERT INTO verification_reports (stop_id, report_type, safety_rating, reported_by) VALUES
(1, 'stop_confirm', 5, 1),
(1, 'stop_confirm', 4, 1),
(1, 'safe_pickup', 5, 1),
(4, 'stop_confirm', 4, 2),
(4, 'stop_confirm', 5, 1),
(4, 'stop_confirm', 4, 1);
