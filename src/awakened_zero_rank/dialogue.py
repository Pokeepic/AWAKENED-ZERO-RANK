from __future__ import annotations

from dataclasses import dataclass

from .models import DialogueExchange, Protagonist, Relationship


@dataclass(frozen=True)
class DialogueIntent:
    name: str
    ren_line: str


INTENTS = {
    "Express gratitude": DialogueIntent(
        "Express gratitude", "You remembered what I said before. Thank you, Aiko."
    ),
    "Ask for guidance": DialogueIntent(
        "Ask for guidance", "What should an F-rank pay attention to if he wants to come back alive?"
    ),
    "Offer support": DialogueIntent(
        "Offer support", "You look exhausted too. I can stay and help with the reports."
    ),
    "Hide worry": DialogueIntent(
        "Hide worry", "I'm fine. It was only a low-rank gate."
    ),
    "Apologize": DialogueIntent(
        "Apologize", "I was short with you before. That wasn't fair. I'm sorry."
    ),
}


def choose_intention(p: Protagonist, relationship: Relationship) -> tuple[DialogueIntent, str]:
    """Choose a transparent social strategy from Ren's lived condition."""
    if relationship.tension >= 12:
        return INTENTS["Apologize"], "their unresolved tension matters more than pride"
    if p.health < 55 or p.injuries > p.missions_completed:
        return INTENTS["Hide worry"], "he feels vulnerable and is not ready to admit it"
    if relationship.trust >= 18 and p.morale >= 48:
        return INTENTS["Offer support"], "trust makes him notice Aiko's burden"
    if relationship.meetings >= 2:
        return INTENTS["Express gratitude"], "he remembers her earlier kindness"
    return INTENTS["Ask for guidance"], "survival matters more than pretending to know everything"


def resolve_aiko_dialogue(p: Protagonist, day: int) -> tuple[DialogueExchange, str]:
    relationship = p.relationships["Aiko Sato"]
    intent, reason = choose_intention(p, relationship)

    if intent.name == "Apologize":
        npc_line = "Thank you for saying it. Let's start again."
        reaction, trust, familiarity, affection, tension = "relieved", 5, 4, 1, -12
    elif intent.name == "Hide worry":
        if relationship.trust >= 15:
            npc_line = "You don't have to perform being fine for me, Ren."
            reaction, trust, familiarity, affection, tension = "concerned", 2, 5, 2, 3
        else:
            npc_line = "Then at least file the injury report before you leave."
            reaction, trust, familiarity, affection, tension = "unconvinced", -1, 2, 0, 5
    elif intent.name == "Offer support":
        npc_line = "You came here injured and you're worried about my paperwork? ...One stack."
        reaction, trust, familiarity, affection, tension = "quietly touched", 5, 6, 3, -2
    elif intent.name == "Express gratitude":
        npc_line = "Most hunters forget advice the moment the gate opens. I'm glad you didn't."
        reaction, trust, familiarity, affection, tension = "pleased", 4, 5, 2, -1
    else:
        npc_line = "Watch the exits before the monsters. Threat Sense is useful only if you listen to it."
        reaction, trust, familiarity, affection, tension = "attentive", 3, 5, 1, 0

    relationship.change(trust, familiarity)
    relationship.affection = max(-100, min(100, relationship.affection + affection))
    relationship.tension = max(0, min(100, relationship.tension + tension))
    relationship.last_reaction = reaction
    p.social_confidence += int(trust > 0 and p.social_confidence < 100)
    p.morale += 5 if trust > 0 else -3
    exchange = DialogueExchange(day, intent.name, intent.ren_line, relationship.name, npc_line, reaction)
    p.dialogue_history.append(exchange)
    del p.dialogue_history[:-20]
    return exchange, reason
