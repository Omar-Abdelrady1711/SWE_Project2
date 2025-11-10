Currently this is just a mock page for the front end, it's not connected to the back end but it's created so that we're able to connect it in the future.

directories and files are:

services/apiClient.js: one axios instance; easy token injection later.
context/AuthContext.jsx: central place to store auth state (token, user); login page can call login().
utils/storage.js: token persistence (localStorage) isolated.
styles/global.css: minimal styling now, accessible by default; you can swap in Tailwind later without rewriting logic.

we do not have a register page since we are not making it accessible for new users to sign up, this will only be a feature for admins to create the accounts to users.
