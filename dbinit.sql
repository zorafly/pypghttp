DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users(
       apikey uuid PRIMARY KEY,
       tokens integer,     /* Number of available generations */
       free_per_month integer, /* Free tokens granted per month */
       /* Identifying information */
       username varchar(128) UNIQUE,
       passhash varchar(128),       
       salt varchar(32),
       phone varchar(32),    /* Phone number */
       reset varchar(8),     /* Reset token */
       verified boolean,     /* True when user has verified phone number */
       last_reset timestamp, /* Time of last reset request */
       created timestamp,    /* Time of creation */
       last_req timestamp,   /* Time of last request */
       last_ip inet,         /* Last IP address connected from */
       /* Safety & Moderation */
       reports integer,      /* Total reports received for user */
       score integer,        /* Average Safety Score */
       watch boolean,        /* True if user is potentially abusive */
       ban   boolean         /* True if user is banned */
);

DROP VIEW IF EXISTS expired_users CASCADE;
CREATE VIEW expired_users AS
       SELECT apikey FROM users WHERE verified = FALSE AND
       	      (created + interval '15 minutes') <= clock_timestamp();

DROP TABLE IF EXISTS creations CASCADE;
CREATE TABLE creations(
       cid uuid PRIMARY KEY,
       uid uuid REFERENCES users(apikey),
       fileid varchar(128), /* B2 File ID for saved image */
       thumbid varchar(128),
       saved integer,
       created timestamp,
       /* Output */
       content varchar(16384),
       /* User Engagement */
       stars integer, /* Number of starred reactions */
       /* Safety & Moderation */
       reports integer, /* Total reports received for item */
       score integer,   /* Calculated Safety Score for this item */
       /* Language model configuration */
       model varchar(32),
       temperature float,
       max_tokens integer,       
       /* Text attributes */
       itemtype varchar(32), /* Type of creation - story, myth, folktale.. */
       setting varchar(32),  /* Setting/universe */
       /* Text modifiers */
       mod1 varchar(32),
       mod2 varchar(32),
       mod3 varchar(32),
       /* Image attributes */
       image_type varchar(32),
       image_style varchar(32),
       /* Image modifiers */
       image_mod1 varchar(32),
       image_mod2 varchar(32),	
       image_mod3 varchar(32)
);

DROP TABLE IF EXISTS jobs CASCADE;
CREATE TABLE jobs(
       jid uuid PRIMARY KEY,
       uid uuid REFERENCES users(apikey) UNIQUE,
       created timestamp,
       status integer,
       error varchar(128)
);

DROP VIEW IF EXISTS expired_jobs CASCADE;
CREATE VIEW expired_jobs AS
       SELECT jid FROM jobs WHERE
              (created + interval '15 minutes') <= clock_timestamp();

DROP TABLE IF EXISTS favorites CASCADE;
CREATE TABLE favorites(
       uid uuid REFERENCES users(apikey),
       cid uuid REFERENCES creations(cid)
);

DROP VIEW IF EXISTS expired_creations CASCADE;
CREATE VIEW expired_creations AS
       SELECT cid,fileid FROM creations WHERE saved = 0 AND
       (created + interval '15 minutes') <= clock_timestamp();

DROP VIEW IF EXISTS recent_creations CASCADE;
CREATE VIEW recent_creations AS
       SELECT cid FROM creations
       WHERE saved = 1
       ORDER BY created DESC
       LIMIT 10;

DROP VIEW IF EXISTS top_creations CASCADE;
CREATE VIEW top_creations AS
       SELECT cid FROM creations
       WHERE saved = 1
       ORDER BY stars DESC
       LIMIT 10;

DROP FUNCTION IF EXISTS browse_creations_page CASCADE;
CREATE FUNCTION browse_creations_page(page int,size int)
       RETURNS TABLE(cid uuid)
       AS $$
       SELECT cid FROM creations
       ORDER BY created DESC
       OFFSET ((page - 1) * size)
       LIMIT size
       $$ LANGUAGE SQL;

DROP FUNCTION IF EXISTS user_creations_page CASCADE;
CREATE FUNCTION user_creations_page(uid uuid,page int,size int)
       RETURNS TABLE(cid uuid)
       AS $$
       SELECT cid FROM creations WHERE
       saved = 1 AND
       uid = uid
       ORDER BY created DESC
       OFFSET ((page - 1) * size)
       LIMIT size
       $$ LANGUAGE SQL;

GRANT ALL PRIVILEGES ON users TO scribble_scribe_dev;
GRANT ALL PRIVILEGES ON creations TO scribble_scribe_dev;
GRANT ALL PRIVILEGES ON recent_creations TO scribble_scribe_dev;
GRANT ALL PRIVILEGES ON top_creations TO scribble_scribe_dev;
GRANT ALL PRIVILEGES ON jobs TO scribble_scribe_dev;



set datestyle = 'POSTGRES';

