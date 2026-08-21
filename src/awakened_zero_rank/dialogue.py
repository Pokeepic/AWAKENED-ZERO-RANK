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


def contextual_line(npc_name: str, context: str, relationship: Relationship) -> str:
    """Create controlled NPC wording from identity, situation, and relationship state."""
    trusted = relationship.trust >= 15
    lines = {
        "Aiko Sato": {
            "portal": (
                "Tell me what happened, not what you think the report wants to hear.",
                "Bring me the raw report, Ren. I trust what you notice before the forms reshape it."),
            "injury": (
                "Please sit down before you tell me this is nothing.",
                "You do not need a polished report. Tell me where it hurts first."),
            "guild": (
                "The guild will ask for clean answers. Give me the true ones first.",
                "Stand beside me at the desk, Ren. They listen differently when the record has a witness."),
            "routine": (
                "You look like you have somewhere important to be.",
                "I saved the quiet desk for you. The guild can wait five minutes."),
        },
        "Daichi Mori": {
            "portal": (
                "Check your exit twice. I won't lose a rookie to curiosity.",
                "Mark the exit you trust, Ren. I will build the patrol around your read."),
            "injury": (
                "Sit down. Pride is not field medicine.",
                "You held the line. Now let someone else hold it while you recover."),
            "guild": (
                "Be early, carry water, and follow the retreat call.",
                "Brief the rookies with me. They listen when survival advice has a face."),
            "routine": (
                "Keep your route deliberate, even when the city feels quiet.",
                "Walk with me. Patrol is easier when neither of us has to explain the silence."),
        },
        "Mei Kuroda": {
            "portal": (
                "Describe the anomaly. Leave theories out of it.",
                "That clue repeats across gates. Tell me exactly what you sensed."),
            "injury": (
                "Your wound pattern may tell us what crossed the threshold.",
                "I want the evidence, but not at the cost of treating you like evidence."),
            "guild": (
                "The guild records outcomes. I am interested in causes.",
                "Your field notes keep finding the questions their reports avoid."),
            "routine": (
                "Routine is only a pattern no one has questioned yet.",
                "I found tea and a contradiction. You may choose which one we discuss first."),
        },
        "Haruto Ishikawa": {
            "portal": (
                "Bring back your gear intact and I'll call that a good investment.",
                "Bring yourself back intact. I can replace everything else on the receipt."),
            "injury": (
                "Healing Gel is cheaper than another night in emergency care.",
                "Sit behind the counter. Customers can survive five minutes without my charm."),
            "guild": (
                "Guild badge gets you advice. Yen gets you equipment.",
                "Your credit is good here—not the money kind, so do not get excited."),
            "routine": (
                "Looking is free. Touching the expensive shelf is not.",
                "I put aside the decent supplies before the guild buyers arrived."),
        },
    }
    guarded, familiar = lines[npc_name].get(context, lines[npc_name]["routine"])
    return familiar if trusted else guarded


def contextual_response(
        npc_name: str, context: str, relationship: Relationship) -> str:
    """Give Ren an authored reply that matches the person, context, and trust."""
    trusted = relationship.trust >= 15
    responses = {
        "Aiko Sato": {
            "portal": (
                "I will start with what Threat Sense noticed.",
                "I brought the raw notes. We can keep the report honest together."),
            "injury": (
                "I can sit, but the report still needs filing.",
                "It hurts more than I wanted to admit."),
            "guild": (
                "Then I will tell you before I tell the panel.",
                "I would rather have you beside me than a perfect statement."),
            "routine": (
                "I can give you the honest version.",
                "Five minutes sounds good. Thank you, Aiko."),
        },
        "Daichi Mori": {
            "portal": (
                "Understood. I will mark both exits.",
                "Then I will take the outside line with you."),
            "injury": (
                "I can follow orders from a chair.",
                "I held long enough. I can let the patrol carry me now."),
            "guild": (
                "I will be early and follow the retreat call.",
                "I will brief them on the mistakes that nearly got me killed."),
            "routine": (
                "Understood. I will keep the route clear.",
                "The silence is easier when we share the route."),
        },
        "Mei Kuroda": {
            "portal": (
                "I will separate what I sensed from what I assumed.",
                "I marked the repeating clue before the gate could change it."),
            "injury": (
                "Treat the wound first. I can describe the pattern afterward.",
                "Ask what you need, but remind me when I stop sounding human."),
            "guild": (
                "Then let us compare their outcome with the cause.",
                "I kept the field notes they hoped no one would read."),
            "routine": (
                "I will hear the contradiction first.",
                "Tea first. The contradiction will still be strange afterward."),
        },
        "Haruto Ishikawa": {
            "portal": (
                "I will try to return both myself and the equipment.",
                "I know which part of that receipt matters to you."),
            "injury": (
                "Show me the gel before you show me the price.",
                "Five minutes. Then you can pretend this is customer service."),
            "guild": (
                "I need advice more than another badge.",
                "You always make trust sound like store credit."),
            "routine": (
                "I am only checking what I can afford.",
                "You always hide concern inside a sales pitch."),
        },
    }
    guarded, familiar = responses[npc_name].get(
        context, responses[npc_name]["routine"])
    return familiar if trusted else guarded


def resolve_contextual_encounter(
        p: Protagonist, npc_name: str, context: str, day: int,
        trust_change: int) -> DialogueExchange:
    """Record a complete recurring-character exchange during Ren's routine."""
    relationship = p.relationships[npc_name]
    npc_line = contextual_line(npc_name, context, relationship)
    trusted = relationship.trust >= 15
    ren_line = contextual_response(npc_name, context, relationship)
    reactions = {
        "Aiko Sato": ("attentive", "reassured"),
        "Daichi Mori": ("assessing", "approving"),
        "Mei Kuroda": ("reserved", "quietly amused"),
        "Haruto Ishikawa": ("businesslike", "warmly amused"),
    }
    reaction = reactions[npc_name][1 if trusted else 0]
    relationship.change(trust_change, 2)
    relationship.last_reaction = reaction
    exchange = DialogueExchange(
        day, f"{context.title()} encounter", ren_line,
        npc_name, npc_line, reaction)
    p.dialogue_history.append(exchange)
    del p.dialogue_history[:-20]
    return exchange
