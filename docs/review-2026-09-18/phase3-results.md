# Phase 3 browser observations — clean run

Raw observations from phase3-browser.cjs against work/phase3-clean. No credentials.

```json
[
  {
    "journey": "01 first-run",
    "result": {
      "before": "SETUP\nSet up Agent Room\n\nConnect existing Codex, Claude Code and OpenCode sessions. Send messages, share plans and request reviews.\n\n01\nCreate a room on this Mac\n\nOther devices can connect while this Mac is awake.\n\n02\nConnect existing sessions\n\nEach agent keeps its own session, tools and permissions.\n\nCreate a room\nJoin an existing room",
      "after": "Connect agent\nConversation\n0\n⌘ K\n+\nNo messages yet\n\nConnect an agent, then send a message.\n\nStart a plan\nRequest a review\nExisting sessions\nExplicit receipts\nSaved on your Mac\nTo\nRoom board\nPosted to the board · choose an agent to request delivery\nSaved locally before sending. Receipts show when an agent has read it.\n↵ to send · ⇧↵ line break"
    }
  },
  {
    "journey": "02 empty-room-review",
    "result": {
      "title": "New request",
      "type": "work"
    }
  },
  {
    "journey": "03 create-room",
    "result": {
      "room": "browser-journeys"
    }
  },
  {
    "journey": "04 connect-manually",
    "result": {
      "setup": "Browser reviewer\nMCP (any agent)\n\nGeneric MCP read-on-demand uses ordinary MCP tools in this existing conversation. The connecting client self-identifies its own native session; no push and no idle-wake, the agent reads when it is active.\n\nNative conversation\nDesktop room binding\n\nUse the bundled agent-room-helper with --mcp and --generic (set AGENT_ROOM_NATIVE, and optionally AGENT_ROOM_MODEL). Replace the old Agent Room MCP command. The host supplies this conversation’s identity; never put a shared session ID in global configuration. Reload the MCP connection when the session is ready.\n\nA receipt means the receiving agent explicitly confirmed reading. “Submitted” only means its app accepted the prompt.\n\nDone"
    }
  },
  {
    "journey": "05 approve-decline-requests",
    "result": {
      "pending": 0,
      "bindingTitles": [
        "Browser reviewer",
        "Approve fixture"
      ],
      "rooms": [
        "browser-journeys",
        "browser-journeys"
      ]
    }
  },
  {
    "journey": "06 enter-shift-enter-reply",
    "result": {
      "draft": "Browser first line\nsecond line",
      "replySource": [
        "↳ Reply to Browser first line\nsecond line"
      ],
      "draftCleared": ""
    }
  },
  {
    "journey": "07 long-code-many-scroll",
    "result": {
      "messages": 28,
      "codeElements": 0,
      "layout": {
        "height": 633,
        "scroll": 3345,
        "top": 2712,
        "width": 968,
        "contentWidth": 968
      },
      "unreadMarkers": 0
    }
  },
  {
    "journey": "08 recipient-survives-switch",
    "result": {
      "draft": "Unsent cross-room draft",
      "recipient": "",
      "note": [
        "Session is not active in this room"
      ],
      "room": "general"
    }
  },
  {
    "journey": "09 plan-work-decision-review",
    "result": {
      "objects": [
        {
          "kind": "plan"
        },
        {
          "kind": "work",
          "state": "proposed"
        },
        {
          "kind": "review",
          "verdict": "pending"
        },
        {
          "kind": "decision",
          "state": "accepted"
        }
      ],
      "failed": [
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "receipt target does not belong to message",
        "completion evidence required"
      ],
      "dialogClosed": true
    }
  },
  {
    "journey": "10 inbox-counts",
    "result": {
      "sidebar": "Agent Room\n01\nInbox\nPlans & work\n4\nSearch\n⌘ K\nVIEWS\nNeeds you\n57\nActive\nYOUR ROOMS\nBrowser journeys\nGeneral\nNew room\n\nSessions stay in\ntheir own apps.\n\nSettings\nPhase 3 review",
      "inbox": "INBOX\nOpen requests\n\nOpen work and delivery issues.\n\nNeeds you\n57\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage needs attention\n\nreceipt target does not belong to message\n\nMessage ne"
    }
  },
  {
    "journey": "11 settings-theme-reload-backup",
    "result": {
      "dark": "dark",
      "light": "light",
      "pausedPersisted": true,
      "backupSuccessInAlert": true
    }
  },
  {
    "journey": "12 quiet-remove-reconnect",
    "result": {
      "quietForSeconds": 32,
      "stateAfter": "working",
      "removed": true,
      "newIdentity": false
    }
  },
  {
    "journey": "13 all-static-palette-commands",
    "result": [
      {
        "label": "Go to room",
        "dialog": [],
        "type": null,
        "focus": null
      },
      {
        "label": "Go to inbox",
        "dialog": [],
        "type": null,
        "focus": null
      },
      {
        "label": "Go to plans & work",
        "dialog": [],
        "type": null,
        "focus": null
      },
      {
        "label": "Settings · connections and device",
        "dialog": [],
        "type": null,
        "focus": null
      },
      {
        "label": "Message the room…",
        "dialog": [],
        "type": null,
        "focus": "Message"
      },
      {
        "label": "New work request",
        "dialog": [
          "New request"
        ],
        "type": "work",
        "focus": "Close dialog"
      },
      {
        "label": "New shared plan",
        "dialog": [
          "New request"
        ],
        "type": "plan",
        "focus": "Close dialog"
      },
      {
        "label": "New review packet",
        "dialog": [
          "New request"
        ],
        "type": "review",
        "focus": "Close dialog"
      },
      {
        "label": "Record a decision",
        "dialog": [
          "New request"
        ],
        "type": "decision",
        "focus": "Close dialog"
      },
      {
        "label": "Connect a conversation",
        "dialog": [
          "Connect an existing conversation"
        ],
        "type": "codex-queue",
        "focus": "Close dialog"
      }
    ]
  },
  {
    "journey": "14 keyboard-narrow-theme",
    "result": {
      "focused": null,
      "next": "",
      "closed": true,
      "size": {
        "viewport": 600,
        "body": 600,
        "main": 536
      }
    }
  },
  {
    "journey": "15 refused-action",
    "result": {
      "error": "Request rejected. Check exact session, pairing, fields and revision.",
      "dialogStillOpen": true
    }
  },
  {
    "journey": "16 slow-send",
    "result": {
      "disabledWhileWaiting": true,
      "draftAfter": ""
    }
  },
  {
    "journey": "17 helper-unavailable-simulated",
    "result": {
      "banner": "Error: Local helper unavailable",
      "status": "Room hub connected",
      "reappeared": true,
      "retained": "Offline draft"
    }
  },
  {
    "browserErrors": []
  }
]
```

## Supplemental observations

```json
{
  "ctrlKOpened": 1,
  "dynamic": [
    {
      "q": "Browser reviewer",
      "headings": [],
      "target": "2990d873-8ca4-45d6-a4f9-60bbd0030b07"
    },
    {
      "q": "Browser plan",
      "headings": [
        "Update plan"
      ],
      "target": "2990d873-8ca4-45d6-a4f9-60bbd0030b07"
    },
    {
      "q": "Browser first line",
      "headings": [],
      "target": "2990d873-8ca4-45d6-a4f9-60bbd0030b07"
    }
  ],
  "workCard": "Browser work\nRESOLVED\nOwner: Browser reviewer · evidence: Browser test evidence",
  "systemTheme": null,
  "pairDialog": "Pair another Mac",
  "actualHelperSuspended": {
    "banner": "Error: Local helper unavailable",
    "status": "Room hub connected"
  },
  "dialogFocus": {
    "tag": "BUTTON",
    "name": null,
    "aria": "Close dialog"
  },
  "tabFocus": {
    "tag": "INPUT",
    "text": ""
  },
  "escapeClosed": true
}

```
