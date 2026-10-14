/// Data shapes mirror the native backend (server/) responses the desktop uses.
/// Parsers are defensive so a backend tweak never crashes the UI.

String _s(dynamic v, [String d = '']) => v == null ? d : v.toString();
int _i(dynamic v, [int d = 0]) => v is int ? v : int.tryParse('$v') ?? d;
double _d(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;

class Health {
  final bool ok;
  final String engine;
  final bool voiceEnabled;
  final String ollamaModel;
  Health({required this.ok, required this.engine, required this.voiceEnabled, required this.ollamaModel});
  factory Health.fromJson(Map<String, dynamic> j) => Health(
        ok: j['ok'] == true,
        engine: _s(j['engine'], 'engine'),
        voiceEnabled: j['voice_enabled'] == true,
        ollamaModel: _s(j['ollama_model']),
      );
  bool get isClaude => engine.contains('Claude');
}

class AgentMeta {
  final String name;
  final String avatar;
  AgentMeta(this.name, this.avatar);
}

class Project {
  final String id;
  final String name;
  final String type;
  final String stack;
  final String description;
  final List<String> members;
  final List<AgentMeta> agentsMeta;
  final bool periodicEnabled;
  final String periodicLabel;

  Project({
    required this.id,
    required this.name,
    required this.type,
    required this.stack,
    required this.description,
    required this.members,
    required this.agentsMeta,
    required this.periodicEnabled,
    required this.periodicLabel,
  });

  factory Project.fromJson(Map<String, dynamic> j) {
    final members = ((j['members'] ?? []) as List).map((e) => e.toString()).toList();
    final meta = ((j['agentsMeta'] ?? []) as List)
        .map((e) => AgentMeta(_s((e as Map)['name']), _s(e['avatar'], 'generic')))
        .toList();
    final per = (j['periodic'] ?? {}) as Map?;
    return Project(
      id: _s(j['id'] ?? j['identifier']),
      name: _s(j['name'], '(unnamed)'),
      type: _s(j['type']),
      stack: _s(j['stack']),
      description: _s(j['description']),
      members: members,
      agentsMeta: meta,
      periodicEnabled: per?['enabled'] == true,
      periodicLabel: _s(per?['cadence'] ?? per?['every'] ?? ''),
    );
  }

  String avatarFor(String member) {
    for (final m in agentsMeta) {
      if (m.name == member) return m.avatar;
    }
    return member.toLowerCase();
  }
}

class Role {
  final String name;
  final String group;
  final String icon;
  final bool ready;
  final List<String> missing;
  final String description;
  Role({
    required this.name,
    required this.group,
    required this.icon,
    required this.ready,
    required this.missing,
    required this.description,
  });
  factory Role.fromJson(Map<String, dynamic> j) => Role(
        name: _s(j['name']),
        group: _s(j['group'], 'tech'),
        icon: _s(j['icon'], '🤖'),
        ready: j['ready'] == true,
        missing: ((j['missing'] ?? []) as List).map((e) => e.toString()).toList(),
        description: _s(j['description'] ?? j['role']),
      );
}

class Connector {
  final String id;
  final String name;
  final String status;
  final String type;
  Connector({required this.id, required this.name, required this.status, required this.type});
  factory Connector.fromJson(Map<String, dynamic> j) => Connector(
        id: _s(j['id']),
        name: _s(j['name']),
        status: _s(j['status'], 'unknown'),
        type: _s(j['type']),
      );
  bool get connected => status == 'connected';
}

class CompanyAgent {
  final String name;
  final String avatar;
  final String description;
  CompanyAgent({required this.name, required this.avatar, required this.description});
  factory CompanyAgent.fromJson(Map<String, dynamic> j) => CompanyAgent(
        name: _s(j['name']),
        avatar: _s(j['avatar'], 'generic'),
        description: _s(j['description']),
      );
}

class Activity {
  final String pid;
  final String agent;
  final String task;
  final String phase;
  Activity({required this.pid, required this.agent, required this.task, required this.phase});
  factory Activity.fromJson(Map<String, dynamic> j) => Activity(
        pid: _s(j['pid']),
        agent: _s(j['agent']),
        task: _s(j['task']),
        phase: _s(j['phase'], 'working'),
      );
  String get key => '$pid:$agent';
}

class Operation {
  final String id;
  final String pid;
  final String kind;
  final String status;
  final String question;
  final List<String> log;
  Operation({
    required this.id,
    required this.pid,
    required this.kind,
    required this.status,
    required this.question,
    required this.log,
  });
  factory Operation.fromJson(Map<String, dynamic> j) => Operation(
        id: _s(j['id']),
        pid: _s(j['pid']),
        kind: _s(j['kind'] ?? j['type']),
        status: _s(j['status'], 'unknown'),
        question: _s(j['question']),
        log: ((j['log'] ?? j['lines'] ?? []) as List).map((e) => e.toString()).toList(),
      );
}

class AnchorRequest {
  final String id;
  final String project;
  final String status;
  final dynamic result;
  final int webhookAttempts;
  final bool acked;
  final String error;
  final double updated;
  AnchorRequest({
    required this.id,
    required this.project,
    required this.status,
    required this.result,
    required this.webhookAttempts,
    required this.acked,
    required this.error,
    required this.updated,
  });
  factory AnchorRequest.fromJson(Map<String, dynamic> j) => AnchorRequest(
        id: _s(j['id']),
        project: _s(j['project']),
        status: _s(j['status'], 'unknown'),
        result: j['result'],
        webhookAttempts: _i(j['webhook_attempts']),
        acked: j['acked'] == true,
        error: _s(j['error']),
        updated: _d(j['updated']),
      );
  bool get isTerminal => status == 'finished' || status == 'failed' || status == 'cancelled';
}
