-- MySQL CRUD from the command line, on BloodLink's real tables.
-- Run after `python manage.py migrate` and `python manage.py seed`:
--     mysql -u bloodlink -p bloodlink < sql/crud_demo.sql
-- (password: bloodlink123)  Or open `mysql -u bloodlink -p bloodlink` and paste one query at a time.

-- Look around -------------------------------------------------------------
SHOW TABLES;
DESCRIBE core_donor;

-- READ: how many donors of each blood group?
SELECT blood_group, COUNT(*) AS donors,
       SUM(is_available) AS available_now
FROM core_donor
GROUP BY blood_group
ORDER BY donors DESC;

-- READ: open requests, most urgent first, with who posted them (JOIN)
SELECT r.id, r.blood_group, r.units_needed, r.hospital, r.city, r.urgency, u.username AS posted_by
FROM core_bloodrequest r
JOIN auth_user u ON u.id = r.posted_by_id
WHERE r.status = 'open'
ORDER BY FIELD(r.urgency, 'critical', 'urgent', 'normal'), r.needed_by;

-- READ: donors who could give to an O+ patient in Jaipur and are eligible
-- (90+ days since last donation, or never donated)
SELECT full_name, blood_group, city, last_donation
FROM core_donor
WHERE blood_group IN ('O-', 'O+')
  AND city = 'Jaipur'
  AND is_available = 1
  AND (last_donation IS NULL OR last_donation <= CURDATE() - INTERVAL 90 DAY);

-- CREATE: post a new request as the demo user ------------------------------
INSERT INTO core_bloodrequest
  (posted_by_id, patient_name, blood_group, units_needed, hospital, city,
   contact_phone, urgency, needed_by, note, status, created_at)
VALUES
  ((SELECT id FROM auth_user WHERE username = 'demo'),
   'CLI Demo Patient', 'A+', 2, 'Eternal Hospital', 'Jaipur',
   '9000000001', 'urgent', CURDATE() + INTERVAL 1 DAY, 'Inserted from the MySQL command line', 'open', NOW());

SET @new_id = LAST_INSERT_ID();
SELECT * FROM core_bloodrequest WHERE id = @new_id;

-- UPDATE: one more unit is needed and it became critical
UPDATE core_bloodrequest
SET units_needed = 3, urgency = 'critical'
WHERE id = @new_id;
SELECT id, patient_name, units_needed, urgency FROM core_bloodrequest WHERE id = @new_id;

-- UPDATE: a moderator verifies every donor in Delhi
UPDATE core_donor SET is_verified = 1 WHERE city = 'Delhi';

-- DELETE: remove the demo request again
DELETE FROM core_bloodrequest WHERE id = @new_id;
SELECT COUNT(*) AS should_be_zero FROM core_bloodrequest WHERE id = @new_id;
