/**
 * MSW Server Setup
 *
 * Create MSW server for Node.js tests.
 */

import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
