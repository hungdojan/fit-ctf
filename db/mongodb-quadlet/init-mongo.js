// MongoDB initialization script
// Creates a user with readWrite role on the application database

// Get environment variables (set by MONGO_INITDB_*)
const dbName = process.env.MONGO_INITDB_DATABASE || 'fit_ctf';
const appUsername = process.env.MONGO_APP_USERNAME || 'fit_ctf_user';
const appPassword = process.env.MONGO_APP_PASSWORD || 'fit_ctf_password';

// Switch to the application database
db = db.getSiblingDB(dbName);

// Create application user with readWrite role
db.createUser({
  user: appUsername,
  pwd: appPassword,
  roles: [
    {
      role: 'readWrite',
      db: dbName
    }
  ]
});
