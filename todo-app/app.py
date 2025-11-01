"""
Simple TODO App - Example client application to demonstrate SENTRIX integration
This is the backend API that will be protected by SENTRIX
"""

from flask import Flask, jsonify, request
from datetime import datetime
import uuid

app = Flask(__name__)

# In-memory database (for demo purposes)
todos = {}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'todo-app'})

@app.route('/api/todos', methods=['GET'])
def get_todos():
    """Get all todos"""
    return jsonify({
        'success': True,
        'todos': list(todos.values()),
        'count': len(todos)
    })

@app.route('/api/todos', methods=['POST'])
def create_todo():
    """Create a new todo"""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'success': False, 'error': 'Title is required'}), 400
    
    todo_id = str(uuid.uuid4())
    todo = {
        'id': todo_id,
        'title': data['title'],
        'description': data.get('description', ''),
        'completed': False,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    todos[todo_id] = todo
    
    return jsonify({
        'success': True,
        'todo': todo
    }), 201

@app.route('/api/todos/<todo_id>', methods=['GET'])
def get_todo(todo_id):
    """Get a specific todo"""
    if todo_id not in todos:
        return jsonify({'success': False, 'error': 'Todo not found'}), 404
    
    return jsonify({
        'success': True,
        'todo': todos[todo_id]
    })

@app.route('/api/todos/<todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Update a todo"""
    if todo_id not in todos:
        return jsonify({'success': False, 'error': 'Todo not found'}), 404
    
    data = request.get_json()
    todo = todos[todo_id]
    
    if 'title' in data:
        todo['title'] = data['title']
    if 'description' in data:
        todo['description'] = data['description']
    if 'completed' in data:
        todo['completed'] = data['completed']
    
    todo['updated_at'] = datetime.utcnow().isoformat()
    
    return jsonify({
        'success': True,
        'todo': todo
    })

@app.route('/api/todos/<todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Delete a todo"""
    if todo_id not in todos:
        return jsonify({'success': False, 'error': 'Todo not found'}), 404
    
    del todos[todo_id]
    
    return jsonify({
        'success': True,
        'message': 'Todo deleted'
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    completed = sum(1 for todo in todos.values() if todo['completed'])
    pending = len(todos) - completed
    
    return jsonify({
        'success': True,
        'stats': {
            'total': len(todos),
            'completed': completed,
            'pending': pending
        }
    })

if __name__ == '__main__':
    # Add some initial todos for demonstration
    initial_todos = [
        {'title': 'Integrate SENTRIX security', 'description': 'Add API security protection'},
        {'title': 'Deploy to production', 'description': 'Deploy the app'},
        {'title': 'Monitor security events', 'description': 'Check SENTRIX dashboard'}
    ]
    
    for todo_data in initial_todos:
        todo_id = str(uuid.uuid4())
        todos[todo_id] = {
            'id': todo_id,
            'title': todo_data['title'],
            'description': todo_data['description'],
            'completed': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
    
    print("=" * 60)
    print("TODO APP - Backend API Server")
    print("=" * 60)
    print("Server running on: http://localhost:5000")
    print(f"Initial todos created: {len(todos)}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

